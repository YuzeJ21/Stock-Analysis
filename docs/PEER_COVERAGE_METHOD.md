# Industry peer-valuation coverage sample

Discover contains **同行估值覆盖 · 行业样本**; Company Workbench's valuation pane links directly to it. **核查下一家公司** explicitly inspects one requested target. Ordinary reads, switching panes and opening disclosures never fetch sources. **重试所选公司** replaces that target's previous observation; **重新开始样本** clears only this session audit. No persistent checkpoint is silently restored or overwritten.

The declared default queries are AMD, TXN, QCOM, MSFT, JPM, JNJ, XOM, PG, MCD, CAT, NEM, DUK, O, VZ and TSM. The engine accepts at most20 unique normalized symbols. These are specified query targets, including potentially unsupported listing paths; they are not a representative sample, all U.S. companies, active U.S.-domiciled issuers or a market-wide denominator. The existing financial-universe checkpoint remains separate and unchanged.

## Separate stages and denominators

Every requested target remains in the rows and denominator, including source failures, unsupported securities, pending targets and unknown industries. Counts distinguish attempted targets, qualified subject reported-annual diluted P/E, completed bounded-reference assessment, qualified relative comparison and pending targets. Industry groups use independently bound vendor industry and SEC SIC metadata, with the vendor filing matched to the SEC issuer. Valid metadata is not financial qualification. Unknown/unbound attribution remains visible.

A subject blocked before P/E qualification has reference state **not assessed**, with a null accepted-reference count. It does not have zero compatible references. A qualified subject with a completed assessment may have zero, one or two references, withholding comparison. Partial source pauses remain partial; three qualified references can support a comparison while the rest of the bounded candidate list remains incomplete. The UI reports these stages separately.

The primary-gap count records the first blocker per requested target, not every downstream gate. Candidate exclusion counts record checks across targets; the same candidate can appear more than once, so those totals are not unique issuers. At most12 other candidates per subject are attempted in provider-list order. Adapter operation counts include component invocations and may include source-evidence cache reuse; they are not HTTP request totals.

## Progress, evidence and limits

Progress is session-only. Two consecutive subject source failures pause further targets; explicit retry can resume. Existing within-subject source pauses remain. Already attempted failures are not silently retried. A retry failure withdraws that target's previous comparison while retaining other observations. Every read rebuilds financial qualification from underlying source packets, not stored verdicts or counters. Stale/future or changed inputs become withheld without hidden network work.

Repeated classification evidence is stored once by its normalized digest; each original peer packet is reconstructed before its existing seal and source checks are applied. Reusing a fresh receipt preserves its original observation time. This reduces duplicate source material without substituting a cached accepted-peer verdict. Historical private audit exports can be replayed at their recorded observation time; they do not restore current eligibility or prove point-in-time coverage.

Personal Research mode and existing source-rights gates apply. The audit cannot update canonical financials, saved model inputs, research records, readiness, source approvals or financial-universe progress. Commercial use and raw redistribution are not cleared. Desktop/phone and automated results describe engineering behavior at a tested commit; independent-persona, hosted and source-rights decisions remain separate.
