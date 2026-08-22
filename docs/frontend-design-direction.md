# Calm Companion design direction

## Direction

**Organic.** StayLong is a coordination product for older people living alone,
not a clinical dashboard or an eligibility decision engine. A trusted supporter
may join only when the older person chooses. The interface uses the Organic
anchor's sand, oat, sage, clay, terracotta, ochre, and moss tokens with rounded
surfaces and humanist type to make a difficult home task feel calm and deliberate
rather than institutional.

The memorable interaction is the **single next action**. The first screen asks
one plain-language question and exposes one primary action. After a real case is
created, that action becomes a review step and the transparent three-stage path
updates from API-returned facts. The interface does not invent provider activity,
assessment outcomes, or approvals merely to make the screen look complete.

## Product rules

- Show only user-supplied or API-returned case information.
- Keep the sandbox token behind secondary Demo settings, in React state only;
  never persist it in browser storage or present it as a normal product task.
- Make the consent and human-approval boundary visible at the moment a case is
  created.
- Keep emergency routing visible without presenting StayLong as an emergency,
  medical, or crisis service.
- Do not present clinical advice, eligibility decisions, provider selection, or
  payment as an agent action.
- Use 44px minimum interaction targets, large readable type, keyboard focus,
  reduced-motion support, and concise plain-language labels.
