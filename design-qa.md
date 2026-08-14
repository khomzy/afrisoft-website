# Afrisoft Main Website — Design QA

## Evidence

- Source visual truth: `/home/kho/Downloads/afrisoft web updates/` (product imagery and team portraits), with source contact sheet at `/tmp/afrisoft-updates-contact.jpg` (1344 × 1237 px).
- Primary source detail: `/home/kho/Downloads/afrisoft web updates/kuphanda math expert.png` (1366 × 768 px).
- Browser-rendered implementation:
  - `/tmp/afrisoft-main-publish/qa/home-desktop.png` (1440 × 1000 px)
  - `/tmp/afrisoft-main-publish/qa/products-kuphanda-math.png` (1440 × 1000 px)
  - `/tmp/afrisoft-main-publish/qa/products-livcast-creator.png` (1440 × 1000 px)
  - `/tmp/afrisoft-main-publish/qa/about-desktop-full.png` (1425 × 4094 px full-page content capture)
  - `/tmp/afrisoft-main-publish/qa/home-mobile-menu.png` (390 × 844 px)
  - `/tmp/afrisoft-main-publish/qa/products-mobile.png` (390 × 844 px)
  - `/tmp/afrisoft-main-publish/qa/about-mobile.png` (390 × 844 px)
  - `/tmp/afrisoft-main-publish/qa/terms-desktop.png` (1440 × 1000 px)
  - `/tmp/afrisoft-main-publish/qa/terms-mobile.png` (390 × 844 px)
- Side-by-side comparison evidence:
  - `/tmp/afrisoft-main-publish/qa/compare-kuphanda.png` (1696 × 948 px)
  - `/tmp/afrisoft-main-publish/qa/compare-team.png` (1696 × 1148 px)
- CSS viewports: 1440 × 1000 desktop and 390 × 844 mobile.
- Density normalization: all browser captures used `deviceScaleFactor: 1`. Source and implementation were proportionally fit into equal 800 px comparison cells; no density-only findings were filed.
- State: public, unauthenticated, default light theme. Product detail states tested were Kuphanda “Math Expert” and LivCast “Creators”; navigation and contact success states were also tested.

## Findings

No actionable P0, P1 or P2 issues remain.

- Fonts and typography: Space Grotesk display type and Manrope body type retain the established Afrisoft hierarchy. Desktop and mobile wrapping is deliberate, readable and free of truncation.
- Spacing and layout rhythm: desktop product split layouts, team hierarchy and legal document spacing remain balanced. Mobile layouts collapse cleanly with no horizontal overflow. Card radii, borders and elevation are consistent with the existing main-site design language.
- Colors and visual tokens: the existing Afrisoft blue and Kuphanda purple are retained; LivCast remains on the established dark surface. Contrast is clear in the inspected states.
- Image quality and asset fidelity: all supplied product images and six supplied team portraits load successfully. Source subjects remain recognisable, crops are intentional, and the optimized WebP files show no visible compression artifacts. Shantel Moyo uses the requested professional woman icon because no portrait was supplied.
- Copy and content: rotating headings and descriptions correspond to their images. Team roles and qualifications match the supplied brief without adding unprovided credentials. The Terms page is marked as a general draft requiring legal review.
- Icons: Font Awesome icons are consistently sized, aligned and from one family. No custom SVG, CSS art, emoji or placeholder image was substituted for supplied visual assets.
- Responsiveness and accessibility: desktop and mobile have no horizontal overflow; fixed-header anchor offset is present; product tabs expose `role="tab"`, `aria-selected`, keyboard arrow/Home/End navigation and reduced-motion support; all supplied photographs have useful alt text.

## Full-view comparison

The team source contact sheet and the full About page were placed together in `compare-team.png`. The implementation preserves all supplied people, places the CEO first, then operations/research, then technology/design/product leadership, and uses circular portraits as requested. The source is an asset sheet rather than a page mock, so composition fidelity was judged against the user’s hierarchy and established Afrisoft site system rather than as a pixel-identical clone.

## Focused-region comparison

The original Kuphanda Math Expert screenshot and the rendered Kuphanda Math story were placed together in `compare-kuphanda.png`. The full product UI remains legible inside the image frame and the accompanying title and copy accurately explain the source state. Additional focused LivCast and mobile captures verify image fit, story copy and responsive tab treatment.

## Comparison history

1. Initial browser pass found a P2 mobile polish issue: product tabs exposed a browser scrollbar and did not present all four choices cleanly. Fixed by fitting all four tabs within the mobile card and reducing only their mobile padding/type size. Post-fix evidence: `products-mobile.png`.
2. Initial browser pass found a P2 anchor issue: scrolling a product card to the top could place its product mark under the fixed navigation. Fixed with a 110 px product-card scroll margin. Post-fix evidence: `products-mobile.png`.
3. Initial browser pass found a P2 asset-direction issue: Shantel’s fallback icon read as a technical astronaut, not the requested woman icon. Replaced with the Font Awesome professional woman silhouette. Post-fix evidence: `about-desktop-full.png` and `compare-team.png`.

## Interactions and runtime checks

- Product tab click updates selected state, heading, description, image and alt text together.
- Automatic story rotation is enabled at six-second intervals, pauses during hover/focus and is disabled for reduced-motion users.
- Keyboard Left/Right/Home/End changes product tabs.
- Desktop product dropdown opens and reports its expanded state.
- Mobile menu opens and closes correctly.
- Contact form reaches its success state.
- All images loaded on Home and About at desktop and mobile sizes.
- About page includes seven team members, six supplied portraits and one requested icon substitute; Kondwani Ngowela is first in the hierarchy.
- Terms page contains all twelve sections and the legal-review notice.
- Browser console errors checked: none.

## Follow-up polish

- P3: final legal wording should be reviewed by qualified Malawian counsel before payments or commercial contracts are introduced.

## Final result

passed
