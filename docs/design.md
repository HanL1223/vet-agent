# Design: "Field notebook"

Flat, warm and minimal, built around the pet. The owner app is a dashboard of tiles with the
assistant beside it (a tab on phones). The clinic view uses the same parts.

## Where it comes from

- **Earlier panel vote ("Oat & Sage").** A practice manager, a pet-brand designer and an
  accessibility lead all chose warm neutrals, sage for actions and terracotta for overdue. Those
  colour jobs carry over.
- **Reference: the waku-agent dashboard.** We took principles, not assets: flat surfaces with no
  shadows, hairline rules, a mono micro-label, one accent, and a solid ink silhouette as the mark.
  We copy none of its files, tokens, fonts, layout values or mark; its design system and mark are
  proprietary brand assets (see its LICENSE-BRAND). Our palette, fonts, rounded shapes,
  sentence-case buttons and pet marks are our own.
- **Ten comparable products** (Small Door, Modern Animal, Dutch, Joii, PetDesk, Digitail,
  Vetster, Pawp, Covetrus CarePlans, Nest Veterinary) taught one thing above all: put the pet at
  the centre, not the assistant.

## Rules

- **Flat.** No shadows. Panels are a shade lighter than the ground (`--panel` on `--ground`) and
  separated by 1px rules (`--rule`).
- **Each colour has one job.** Sage `--sage` marks actions, with one solid primary button per
  view. Terracotta `--clay` means overdue or lapsed. Red `--urgent` is only for "call the clinic
  now", always with an icon and words. Ink is for data: the latest bar, the weight line, the
  owner's own messages.
- **Status is in words, not only colour** ("21 days overdue", "85% covered"). Dots and strips
  only reinforce the words.
- **Type.** Fraunces for headings and big numbers. Nunito Sans for reading. IBM Plex Mono only
  for uppercase micro-labels (`.label`): tile titles, months, KPI names.
- **The mark is the owner's pet (BR-1).** A solid ink silhouette from `petIcon()`, picked at
  random from the owner's pets on each visit by `paintMark()`. The silhouettes come from
  game-icons.net (CC BY 3.0: dog, rabbit and kiwi by Delapouite, cat by Lorc). Keep the credit
  on the landing page and in the README.
- **Tiles answer one question each:** what needs attention, how they've been this week, are they
  protected, what will this year cost, and their weight. Each has at most one primary action.
- **Contrast (WCAG AA), measured:** muted text 5.9 on ground, overdue text 5.7, white on sage
  6.1, control edges (`--edge`) 3.3, urgent text 5.8 on its tint. Check any new colour first.
- **Don't decorate.** No illustrations, gradients or paw wallpaper. The clinic list stays dense.
