# Evidence One-Pager design QA

## Result

`final result: passed`

All saved images were inspected. There are zero open P0, P1, or P2 findings.
One P3 observation is recorded as intentional polish rather than a blocking
defect.

## Scope and method

- Implementation HEAD: `129129b493265b227ebcbb6f8670a74931df0ec0`.
- State inspected: the deterministic standalone complete-state fixture created
  with the existing `_synthetic_brief("complete")` test seam.
- Fixture HTML:
  `/tmp/stock-evidence-one-pager-design-qa-129129b493265b227ebcbb6f8670a74931df0ec0/complete.html`,
  SHA-256
  `861a8e7048eb00db3fee216a42b1cd989d7236ea6f3351094524bb1c7d870b9d`.
- Accepted screenshots were captured with the repository's Playwright/Chrome
  setup, Google Chrome, browser zoom `100%`, DPR `1`, visual viewport scale
  `1`, and screenshot `scale="device"`.
- The desktop implementation and the approved reference were compared at the
  same native `2310x1504` pixel dimensions. Neither panel was cropped, resized,
  stretched, or content-aware edited.
- The current captures were accepted only after their PNG signatures, exact
  IHDR dimensions, viewport metadata, overflow, and browser-error fields were
  verified.

## Artifact identities

| Artifact | Exact path | SHA-256 | Verified geometry |
| --- | --- | --- | --- |
| Approved reference | `/var/folders/cw/xfqgmp_57rn7nn3fq68z_6280000gn/T/codex-clipboard-80b40520-4c8b-493e-89af-a87e159e329b.png` | `d467ce50f7803b3a269b5cfd748a87c1ce4a269345943ca6993d365056c72d59` | PNG IHDR `2310x1504` |
| Desktop implementation | `/tmp/stock-evidence-one-pager-design-qa-129129b493265b227ebcbb6f8670a74931df0ec0/implementation-desktop-2310x1504.png` | `6395a7b396e0cf014a61d31c1f1ca87ddad03bdfca1dc66d9dd14c5f10091990` | PNG IHDR and CSS viewport `2310x1504` |
| Phone implementation | `/tmp/stock-evidence-one-pager-design-qa-129129b493265b227ebcbb6f8670a74931df0ec0/implementation-phone-390x844.png` | `47c9232768b6030f42c6d5dbfe2c1757f2dcd9097efeaee0ccd9fc1cc297aa47` | PNG IHDR and CSS viewport `390x844` |
| Labeled comparison | `/tmp/stock-evidence-one-pager-design-qa-129129b493265b227ebcbb6f8670a74931df0ec0/reference-vs-implementation-2310x1504.png` | `e2514378e1201fc74b5649d1943f6bb6b343370cc7f974c20527ccbd046b34c1` | PNG IHDR `4700x1624`; equal `2310x1504` panels, `80px` gutter, `120px` label band |

Supporting evidence:

- Capture metadata:
  `/tmp/stock-evidence-one-pager-design-qa-129129b493265b227ebcbb6f8670a74931df0ec0/capture-metadata.json`,
  SHA-256
  `9c177008c08fc4f4280a64d72463c51eea3011a84b7407b17219f4d7e96cf6c8`.
- Composite metadata:
  `/tmp/stock-evidence-one-pager-design-qa-129129b493265b227ebcbb6f8670a74931df0ec0/composite-metadata.json`,
  SHA-256
  `9f58c1f02499bc588dbf0494719089028c6720f7a6a1a45cdad57c05e961f171`.
- Pixel verification:
  `/tmp/stock-evidence-one-pager-design-qa-129129b493265b227ebcbb6f8670a74931df0ec0/pixel-verification.log`,
  SHA-256
  `481d3326573303ebd884cb72a4539512b0f8e5c59cbc248daa67530aabf7d1bd`.
  It records both composite panels as raw-pixel-equal to their source images
  and confirms that labels sit outside the image content.
- Hash ledger:
  `/tmp/stock-evidence-one-pager-design-qa-129129b493265b227ebcbb6f8670a74931df0ec0/visual-hashes.tsv`,
  SHA-256
  `72990560d766305dff6e23e83de3b40f5fb10972deb39da1ca341efbeff18f7e`.

## Findings by severity

| Severity | Count | Finding and disposition |
| --- | ---: | --- |
| P0 | 0 | No blocker, unusable flow, or evidence-boundary breach observed. |
| P1 | 0 | No major hierarchy, readability, clipping, overflow, or interaction defect observed. |
| P2 | 0 | No material responsive, spacing, state, or visual-consistency defect observed. |
| P3 | 1 | At `2310px` wide, the implementation retains the existing centered, narrower Research Brief shell and therefore uses more surrounding whitespace than the dense reference canvas. This is intentional: the approved design preserves the existing report, avoids a fixed dense dashboard canvas, and permits normal scrolling. No change is required for this slice. |

## Visual assessment

- The summary has a distinct dark surface, amber emphasis, legible hierarchy,
  explicit state text, semantic cards, and a clear handoff to the complete
  Research Brief below it.
- State meaning does not depend on color alone. Visible state labels and card
  text remain present in the complete-state capture.
- The complete report remains in the same offline document and is visibly
  reachable by normal vertical scrolling.
- The phone capture reflows to one column. Identity copy wraps without
  collision, and measured document and one-pager horizontal overflow are both
  `0px`.
- Desktop and phone captures recorded no console errors and no page errors.

## Intentional differences from the reference

The implementation follows the reference's visual hierarchy without copying
claims that the frozen evidence does not support:

- no `Certified` badge or certification claim;
- no target price, upside, current-price, or spot-price framing;
- no probability, percentile, or confidence-distribution claim;
- no capital-allocation instruction; and
- no buy, sell, own, invest, or other action language.

Instead, it shows already-frozen evidence, scenario assumptions, independent
state disclosures, blockers, process status, and the next research task. The
scenario naming uses `Bull`, not `Blue Sky`, and the artifact remains English
only for this bounded slice.

## Phone, zoom, and contrast evidence

- Direct capture evidence: desktop `2310x1504@1` and phone `390x844@1`, both
  at browser zoom `100%`, visual viewport scale `1`, with zero document or
  one-pager overflow.
- The bridged standalone aa6 browser packet, result SHA-256
  `2eba7b2a354ba0bcc2cdedb5119f07e21879023722472c79fa64f0b45fcd80b2`,
  covers the complete 24-cell matrix at
  `100%`, `200%`, and `400%` zoom with zero failed assertions.
- The fresh Research accessibility packet on implementation HEAD, SHA-256
  `52c62631274d7f28027f648a98144133cf271b9bf6594cba550d6498bcfd5946`,
  covers existing desktop and phone
  routes plus all three Workbench one-pager cells. The Workbench cells recorded
  minimum text/link contrast `16.644346951453382`, minimum boundary contrast
  `3.6594143300026367`, a `44px` download target, zero overflow, and no
  console/page errors.
- The same browser evidence includes forced-colors and print assertions. These
  are deterministic automated checks, not a claim of human or screen-reader
  validation and not a complete WCAG conformance audit.

## Final decision

The inspected desktop and phone implementation is visually coherent,
responsive, and faithful to the approved evidence boundary. With every P0,
P1, and P2 closed, the visual QA gate passes. The single P3 note is an
intentional shell-width difference and remains non-blocking.
