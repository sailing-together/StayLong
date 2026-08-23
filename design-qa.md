# StayLong Guided Workspace design QA

## Evidence

- Source visual truth: `https://p.superdesign.dev/draft/e9594730-98c6-403c-a932-c975080b5af1`
- Source capture: `/private/tmp/staylong-guided-reference-1280x720.jpg`
- Implementation capture: `/private/tmp/staylong-guided-implementation-1280x720.jpg`
- Side-by-side comparison: `/private/tmp/staylong-guided-comparison-2560x720.jpg`
- Mobile implementation capture: `/private/tmp/staylong-guided-implementation-mobile-390x844.jpg`
- Desktop viewport: 1280 × 720 CSS px, device pixel ratio 2.
- Source pixels: 1280 × 720. Implementation pixels: 1265 × 720 because the local page reserved the vertical scrollbar; normalized to 1280 × 720 for the side-by-side comparison.
- Mobile viewport: 390 × 844 CSS px. The document width remained within the viewport with no horizontal overflow.
- State: initial plan intake; the interaction check additionally selected the Night-time bathroom example and opened Demo settings.

## Findings

No actionable P0, P1, or P2 differences remain in the tested desktop state.

- Fonts and typography: Epilogue is used throughout. Heading weight, scale, wrapping, and line height now follow the selected draft. The older serif marketing typography was removed.
- Spacing and layout rhythm: the compact header, 320 px progress rail, 64 px desktop gap, 760 px task panel, rounded corners, and above-the-fold primary action align with the source composition.
- Colors and visual tokens: sand, sage, clay, terracotta, and moss tokens match the approved Organic direction. No gradients are used.
- Image quality and asset fidelity: the approved `staylong-lockup.svg` is used directly with its natural aspect ratio. No placeholder or reconstructed logo is present.
- Copy and content: the main question, safety boundary, four-stage path, and plan-summary language match the selected product direction.

The following differences are intentional and user-approved:

- Three example choices were added before the free-text field to reduce the blank-page burden for an older person.
- Milestones use visible numbers instead of decorative dots to make sequence and current position easier to understand.
- The compact header includes “Independent living, coordinated” to clarify the product category.

## Interaction and browser checks

- Selecting “Night-time bathroom” populated the editable concern text and set `aria-pressed="true"`.
- Demo settings expanded and exposed the token input.
- The desktop primary action remained visible at 1280 × 720.
- The mobile view switched to the compact “Step 1 of 4” header and stacked example choices into large touch targets.
- Browser console check: no warnings or errors.

## Comparison history

1. Initial implementation used an oversized logo and heading, centered the grid differently from the source, and pushed the primary action below the desktop fold.
2. The logo was returned to the source height, the grid was aligned to the source columns, the heading was reduced to the source scale, and vertical density was tightened.
3. The final comparison confirms that the task panel and progress rail align with the source while retaining the approved example selector.

Focused region comparison was not required: at 1280 × 720, the logo, path labels, heading, choices, input copy, and primary action are all readable in the full-view comparison.

## Follow-up polish

- P3: verify the same responsive layout on a physical older Android phone before production release.

final result: passed
