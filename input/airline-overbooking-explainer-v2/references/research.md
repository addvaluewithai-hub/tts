# Research notes — airline overbooking explainer

Use these sources to verify factual claims during production. Keep hypothetical example numbers clearly labeled as examples.

## U.S. Department of Transportation — Bumping & Oversales
https://www.transportation.gov/individuals/aviation-consumer-protection/bumping-oversales

Key points used:
- Airlines may oversell flights to compensate for no-shows.
- Not all airlines oversell.
- When an oversold flight has more ready-to-board passengers than seats, U.S. airlines must first ask for volunteers before involuntary denied boarding due to oversales.
- Compensation / boarding-priority rules exist, but exact amounts and rules can change and should not be hard-coded into this evergreen script.

## IATA — Overbooking
https://www.iata.org/contentassets/2e46aace261040b9a47fb7b9da18efc9/overbooking.pdf

Key points used:
- Once a flight departs, an empty seat can no longer be sold; airline seats are time-sensitive inventory.
- Airlines can use historical no-show behavior as part of overbooking / revenue-management decisions.

## IATA — Revenue Management
https://www.iata.org/en/training/pages/revenue-management/

Key point used:
- Overbooking management and demand forecasting are established parts of airline revenue management.

## Editorial fact policy

Do not present the 180-seat / 185-ticket scenario as a typical real-world rate. It is an intentionally simple hypothetical example used to visualize the mechanism.
