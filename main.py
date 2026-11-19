"""Forecast GTA VI trophy earn rates on Exophase at a case target.

The program reads one case file per run (every *.in found in the input
directory) and writes one forecast file per case.  Each forecast gives five
quantiles of every trophy's earn rate at the target, in percent.

Two shapes of history are handled.  When every read shows the same tracked
player count and the same rates, the page has not refreshed yet: the forecast
assumes the documented first refresh, in which the tracked count grows about
sixfold while almost every trophy's earned count stays put, except the
trophies at the very top of the rate list, whose new players earn them at a
good fraction of the current rate.  When the reads move, the program fits
separate straight lines for the tracked count and for each trophy's earned
count against log time since release, and reads both lines at the target.

Standard library only, no network, no randomness: two runs agree byte for
byte.
"""

import glob
import json
import math
import os
import sys

# The documented first refresh of the game's page: the tracked count went
# from 638 players to 3868 players while the rates were reprinted.
REFRESH_OLD_PLAYERS = 638.0
REFRESH_NEW_PLAYERS = 3868.0

# Share of the current rate at which the newly tracked players earn the
# fastest trophies during the refresh.
FAST_EARN_SHARE = 0.28

# Width of the central band, in logit units, from the 5% to the 95%
# quantile, for the flat-history forecast.
CORE_WIDTH = 0.10

# How far the upper side of the band stretches for the fast trophies, in
# logit units from the median to the 95% quantile.
FAST_UPPER_WIDTH = 0.30

# Widest band the moving-history forecast may use, in logit units.
MAX_WIDTH = 1.1

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
ZS = (-1.645, -0.674, 0.0, 0.674, 1.645)


def clamp_rate(rate):
    if rate < 0.01:
        return 0.01
    if rate > 99.99:
        return 99.99
    return rate


def to_logit(rate):
    p = clamp_rate(rate) / 100.0
    return math.log(p / (1.0 - p))


def from_logit(value):
    return 100.0 / (1.0 + math.exp(-value))


def quantiles(median, lower_step, upper_step):
    centre = to_logit(median)
    out = []
    for z in ZS:
        step = lower_step if z < 0 else upper_step
        val = from_logit(centre + z * step)
        if val < 0.0:
            val = 0.0
        if val > 100.0:
            val = 100.0
        out.append(round(val, 4))
    for i in range(1, len(out)):
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def fit_line(xs, ys):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = 0.0
    den = 0.0
    for x, y in zip(xs, ys):
        num += (x - mean_x) * (y - mean_y)
        den += (x - mean_x) * (x - mean_x)
    if den <= 0.0:
        return mean_y, 0.0
    slope = num / den
    return mean_y - slope * mean_x, slope


def flat_forecast(last_rates, last_players):
    target_players = last_players * REFRESH_NEW_PLAYERS / REFRESH_OLD_PLAYERS
    newcomers = target_players - last_players
    distinct = sorted({r for r in last_rates if r < 100.0}, reverse=True)
    fast_rates = set(distinct[:3])
    core_step = CORE_WIDTH / (2.0 * 1.645)
    fast_step = FAST_UPPER_WIDTH / 1.645
    rows = []
    for tid, rate in enumerate(last_rates, start=1):
        if rate >= 100.0:
            rows.append({"id": tid, "q": [100.0, 100.0, 100.0, 100.0, 100.0]})
            continue
        earned = rate / 100.0 * last_players
        if rate in fast_rates:
            earned += newcomers * (rate / 100.0) * FAST_EARN_SHARE
            median = 100.0 * earned / target_players
            rows.append({"id": tid, "q": quantiles(median, core_step, fast_step)})
        else:
            median = 100.0 * earned / target_players
            rows.append({"id": tid, "q": quantiles(median, core_step, core_step)})
    return rows


def moving_forecast(case, reads, last_rates, last_players):
    release = case["game"]["release_date"]
    rel_year = int(release[0:4])
    rel_month = int(release[5:7])
    rel_day = int(release[8:10])
    import datetime

    base = datetime.datetime(rel_year, rel_month, rel_day, tzinfo=datetime.timezone.utc)
    times = []
    for read in reads:
        at = read["at"]
        stamp = datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))
        minutes = (stamp - base).total_seconds() / 60.0
        times.append(math.log1p(max(minutes, 0.0)))
    target = case["target"]
    tstamp = datetime.datetime.fromisoformat(target.replace("Z", "+00:00"))
    target_minutes = (tstamp - base).total_seconds() / 60.0
    target_x = math.log1p(max(target_minutes, 0.0))
    last_x = times[-1]
    players_log = [math.log(max(r["players_tracked"], 1)) for r in reads]
    p_inter, p_slope = fit_line(times, players_log)
    players_pred = math.exp(p_inter + p_slope * target_x)
    if players_pred < 1.0:
        players_pred = 1.0
    horizon = max(target_x - last_x, 0.0)
    rows = []
    for tid, rate in enumerate(last_rates, start=1):
        if rate >= 100.0:
            rows.append({"id": tid, "q": [100.0, 100.0, 100.0, 100.0, 100.0]})
            continue
        earned_log = []
        for read in reads:
            r = read["rates"][tid - 1]
            if r is None:
                earned_log.append(math.log(0.5))
            else:
                earned_log.append(math.log(max(r / 100.0 * read["players_tracked"], 0.5)))
        e_inter, e_slope = fit_line(times, earned_log)
        resid = 0.0
        for x, y in zip(times, earned_log):
            resid += (y - (e_inter + e_slope * x)) ** 2
        resid = math.sqrt(resid / max(len(times), 1))
        earned_pred = math.exp(e_inter + e_slope * target_x)
        median = 100.0 * earned_pred / players_pred
        if median < 0.0:
            median = 0.0
        if median > 100.0:
            median = 100.0
        width = 0.10 + 0.35 * resid + 0.15 * math.sqrt(horizon)
        if width > MAX_WIDTH:
            width = MAX_WIDTH
        step = width / (2.0 * 1.645)
        rows.append({"id": tid, "q": quantiles(median, step, step)})
    return rows


def forecast_case(case):
    reads = case["history"]
    last = reads[-1]
    last_rates = last["rates"]
    last_players = last["players_tracked"]
    flat = True
    for read in reads:
        if read["players_tracked"] != last_players:
            flat = False
        if read["rates"] != last_rates:
            flat = False
    if flat:
        return flat_forecast(last_rates, last_players)
    return moving_forecast(case, reads, last_rates, last_players)


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(in_dir, "*.in")))
    for path in paths:
        with open(path, "r", encoding="utf-8") as handle:
            case = json.load(handle)
        rows = forecast_case(case)
        payload = {"trophies": rows}
        name = os.path.splitext(os.path.basename(path))[0] + ".out"
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
