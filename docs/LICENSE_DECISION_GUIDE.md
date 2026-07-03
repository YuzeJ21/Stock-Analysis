# License Decision Guide

The repository now has a root `LICENSE` with controlled portfolio-demo terms.
That keeps the product shareable for review while avoiding accidental
open-source or broad reuse-rights claims.

Current path: controlled portfolio/demo evaluation. Visitors can read and run
the product for evaluation, but reuse, redistribution, sublicensing, hosted
service use, and modified-publication rights are not granted without written
permission.

If the project later needs broader distribution, choose one of these paths and
update both `LICENSE` and the README License section:

| Goal | Common path | Visitor expectation |
| --- | --- | --- |
| Controlled portfolio showcase | Keep the current controlled demo license | Visitors can review the project, but reuse rights are not granted. |
| Let others reuse with attribution | Add MIT or Apache-2.0 | Visitors can reuse under the selected license terms. |
| Keep stronger control | Add a custom or proprietary notice | Visitors should ask before reuse; use legal review for custom wording. |

Do not claim the project is open source unless `LICENSE` is replaced with an
open-source license and README wording is updated to match. Also do not hide
normal Python dependencies; the product can truthfully say the application logic
is implemented in project code and built with the Python data ecosystem.

License status is a packaging/share gate only. It does not refresh data, unlock
blocked inputs, or change research readiness.
