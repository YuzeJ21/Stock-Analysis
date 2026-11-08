"""Private issuer-scoped user records; no company inputs or source refresh required."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from itertools import islice
import csv
import re

from src.catalyst_evidence_timeline import load_catalyst_events
from src.research_outcome_review import load_outcomes
from src.research_record_authoring import AuthoringPaths
from src.research_thesis_journal import load_journal_entries
from src.sec_research_review import _ticker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_NOTE_BYTES = 2 * 1024 * 1024
MAX_NOTE_SCOPES = 100


@dataclass(frozen=True)
class CompanyNotesScope:
    profile_key: str
    ticker: str
    sec_cik: str

    def __post_init__(self):
        _profile(self.profile_key)
        if not _ticker(self.ticker) or not valid_notes_cik(self.sec_cik):
            raise ValueError('Invalid saved note scope')


@dataclass(frozen=True)
class CompanyNotes:
    scope: CompanyNotesScope
    journal: tuple
    catalysts: tuple
    outcomes: tuple

    @property
    def record_count(self):
        return len(self.journal) + len(self.catalysts) + len(self.outcomes)


@dataclass(frozen=True)
class NotesIndex:
    scopes: tuple[CompanyNotesScope, ...]
    errors: tuple[str, ...]


def valid_notes_cik(value):
    return isinstance(value, str) and re.fullmatch('[0-9]{10}', value) is not None and int(value) > 0


def _profile(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200 or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid research profile')
    return sha256(value.encode()).hexdigest()


def _base(project_root=None):
    return Path(PROJECT_ROOT if project_root is None else project_root).resolve() / 'outputs/local/company-research-notes'


def _safe_path(path, base):
    # Reject symlinked parents as well as files, including a redirected store root.
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('Saved notes contain a symlink')
        if part == base.parent.parent.parent:
            break
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError('Saved note scope escaped its store')
    return path


def notes_paths(scope, *, project_root=None):
    if not isinstance(scope, CompanyNotesScope):
        raise ValueError('Invalid saved note scope')
    base = _base(project_root)
    directory = base / _profile(scope.profile_key) / scope.sec_cik / scope.ticker
    paths = AuthoringPaths(*(directory / name for name in (
        'research_thesis_journal.csv', 'catalyst_evidence.csv', 'research_outcome_reviews.csv')),
        max_bytes=MAX_NOTE_BYTES)
    for path in paths.all():
        _safe_path(path, base)
    return paths


def load_company_notes(scope, *, project_root=None):
    paths = notes_paths(scope, project_root=project_root)
    for path in paths.all():
        if path.exists() and (not path.is_file() or path.stat().st_size > MAX_NOTE_BYTES):
            raise ValueError('Saved note file limit exceeded')
    try:
        journal = load_journal_entries(paths.journal)
        catalysts = load_catalyst_events(paths.catalysts)
        outcomes = load_outcomes(paths.outcomes)
    except (csv.Error, UnicodeError) as exc:
        raise ValueError('Saved note records could not be parsed') from exc
    for row in (*journal, *catalysts, *outcomes):
        if row.profile_key != scope.profile_key or row.ticker != scope.ticker:
            raise ValueError('Saved record does not match note scope')
    return CompanyNotes(scope, journal, catalysts, outcomes)


def notes_index(profile_key, *, project_root=None):
    base = _base(project_root)
    directory = _safe_path(base / _profile(profile_key), base)
    if not directory.exists():
        return NotesIndex((), ())
    scopes, errors = [], []
    issuers = sorted(islice(directory.iterdir(),MAX_NOTE_SCOPES+1))
    if len(issuers) > MAX_NOTE_SCOPES:
        errors.append('Additional saved note scopes exceed this bounded Monitor list. Exact saved-note links remain available.')
        issuers=issuers[:MAX_NOTE_SCOPES]
    examined=0
    for issuer in issuers:
        try:
            _safe_path(issuer, base)
            if not issuer.is_dir() or not valid_notes_cik(issuer.name):
                raise ValueError('Invalid saved issuer scope')
            companies = sorted(islice(issuer.iterdir(),MAX_NOTE_SCOPES+1))
            for company in companies:
                if examined>=MAX_NOTE_SCOPES:
                    errors.append('Additional saved note scopes exceed this bounded Monitor list. Exact saved-note links remain available.')
                    break
                examined+=1
                try:
                    scope = CompanyNotesScope(profile_key, company.name, issuer.name)
                    if load_company_notes(scope, project_root=project_root).record_count:
                        scopes.append(scope)
                except (ValueError, OSError):
                    errors.append('A saved company note scope could not be verified.')
        except (ValueError, OSError):
            errors.append('A saved issuer note scope could not be verified.')
    return NotesIndex(tuple(scopes), tuple(errors))


def saved_notes_scope(ticker, profile_key, *, sec_cik=None, project_root=None):
    if not _ticker(ticker) or sec_cik is not None and not valid_notes_cik(sec_cik):
        return None
    try:
        if sec_cik is not None:
            scope=CompanyNotesScope(profile_key,ticker,sec_cik)
            return scope if load_company_notes(scope,project_root=project_root).record_count else None
        matches = [s for s in notes_index(profile_key, project_root=project_root).scopes
                   if s.ticker == ticker and (sec_cik is None or s.sec_cik == sec_cik)]
        return matches[0] if len(matches) == 1 else None
    except (ValueError, OSError):
        return None


def notes_query(scope):
    return dict(mode='research', page='company-workbench', ticker=scope.ticker,
                section='notes', notes_cik=scope.sec_cik)


def saved_company_notes_scope(ticker,profile_key,*,sec_cik=None,project_root=None):
    """Resolve saved note or SEC-receipt identity, never a current listing claim."""
    if not _ticker(ticker) or sec_cik is not None and not valid_notes_cik(sec_cik):return None
    try:
        if sec_cik is not None:
            existing=saved_notes_scope(ticker,profile_key,sec_cik=sec_cik,project_root=project_root)
            if existing:return existing
        from src.sec_research_review import list_reviews
        packets=list_reviews(PROJECT_ROOT if project_root is None else project_root,profile_key,ticker)
        ciks={packet['sec_cik'] for packet in packets if sec_cik is None or packet['sec_cik']==sec_cik}
        if sec_cik is None:
            index=notes_index(profile_key,project_root=project_root)
            if index.errors:return None
            ciks.update(scope.sec_cik for scope in index.scopes if scope.ticker==ticker)
        return CompanyNotesScope(profile_key,ticker,next(iter(ciks))) if len(ciks)==1 else None
    except (ValueError,OSError):return None


def legacy_note_tickers(paths, profile_key):
    """Find existing user records without assigning their ticker-only scope a CIK."""
    _profile(profile_key)
    if not isinstance(paths,AuthoringPaths):
        raise ValueError('Invalid legacy research paths')
    for path in paths.all():
        if path.is_symlink() or path.exists() and not path.is_file():
            raise ValueError('Legacy research file could not be verified')
    try:
        groups=(load_journal_entries(paths.journal),load_catalyst_events(paths.catalysts),load_outcomes(paths.outcomes))
    except (csv.Error,UnicodeError) as exc:
        raise ValueError('Legacy research records could not be parsed') from exc
    return tuple(sorted({row.ticker.upper() for rows in groups for row in rows
                         if row.profile_key==profile_key and _ticker(row.ticker.upper())}))


def legacy_notes_available(ticker,profile_key,paths):
    if not _ticker(ticker):return False
    try:return ticker in legacy_note_tickers(paths,profile_key)
    except (ValueError,OSError):return False
