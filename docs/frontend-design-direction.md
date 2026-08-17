# Family workspace design direction

## Direction

**Organic.** StayLong is a coordination product for authorised family members,
not a clinical dashboard or an eligibility decision engine. The interface uses
sand, sage, terracotta, and moss tones with rounded surfaces and humanist type
to make a difficult household task feel calm and deliberate rather than
institutional.

The memorable interaction is the **case path**: it stays empty until a real
case is created, then exposes the known concern and the next safe boundary. It
does not invent service-provider activity, assessment outcomes, or approval
states merely to make the screen look complete.

## Product rules

- Show only user-supplied or API-returned case information.
- Keep the access token in React state only; never persist it in browser storage.
- Make the consent and human-approval boundary visible at the moment a case is
  created.
- Do not present clinical advice, eligibility decisions, provider selection, or
  payment as an agent action.
- Use inclusive, legible interaction targets and concise plain-language labels.
