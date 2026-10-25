# Design: "Oat & Sage"

Warm, clean, minimal and pet-first. Chosen from four directions by a panel vote (practice manager,
pet-brand designer, accessibility lead), with all three votes for this one.

## References

Ten comparable products we studied: Small Door, Modern Animal, Dutch, Joii, PetDesk, Digitail,
Vetster, Pawp, Covetrus CarePlans, Nest Veterinary. The common lesson: put the pet, not the
assistant, at the centre. Use warm neutrals instead of clinical teal, a calm hospitality tone, plain
membership value, and practical lists for clinic tools.

## Rules

- **Colour has one job each.** Sage `--sage` marks actions, and each view has one solid primary
  button. Terracotta `--clay` means overdue. Red `--urgent` is only for "call the clinic now",
  always shown with an icon and words. Due soon uses sage text and a hollow dot.
- **Status uses words, not only colour** ("21 days overdue"). The dot just reinforces them.
- **Type:** Fraunces for headings and big numbers, Nunito Sans for everything else.
- **Pets get faces:** use `petIcon(species)` from `common.js` instead of letter avatars. Use the
  paw (`PAW`) only for the clinic mark.
- **Agent replies are plain text, not chat bubbles.** Only the owner's messages are bubbles. The
  AG-7 action list is a quiet caption with a check mark. The model name lives in the data sheet.
- **Contrast (WCAG AA):** white on sage 6.1, overdue text on cream 5.8, muted text on cream 5.8,
  and outlines of controls (`--edge`) at least 3:1. Check new colours before using them.
- **Don't over-decorate.** No paw wallpaper or extra tints. The clinic list stays dense.
