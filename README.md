# Trophy Dilution Forecaster v6

A Python forecaster for the GTA VI trophy rates on Exophase. It reads one
case at a time, works out where each trophy's earn rate is heading by the
case target, and writes five quantiles per trophy.

[![make.fun bounty](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01)
[![entry rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/rohitchanuwu69-bot/gta6-trophy-rarity-forecast-01-v6/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01)
[![entry reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/rohitchanuwu69-bot/gta6-trophy-rarity-forecast-01-v6/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01)

The idea in one line: when the tracked page has not refreshed yet, most
trophies keep their earned counts while the player count jumps, and only the
fastest few trophies pick up new earners; when the reads move, the program
fits growth lines for players and earned counts against log time instead.

Run it locally with:

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Entered in [Forecast how many GTA VI players earn each trophy in week one](https://make.fun/bounty/gta6-trophy-rarity-forecast-01) on make.fun. Play along via [my referral link](https://make.fun/r/s1fmr9k0).
