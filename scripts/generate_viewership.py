from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"

# ---------- Rules ----------
DATA_START = pd.Timestamp("2025-01-01")
DATA_END = pd.Timestamp("2025-12-31")
SPIKE_START = pd.Timestamp("2025-04-10")
SPIKE_END = pd.Timestamp("2025-04-24")

TARGET_BASE_ROWS = 48_000     # regular viewing; spike sessions are added on top
EXTRA_SPIKE_MEAN = 0.6        # extra live-sport sessions per active user in the spike window
SPORT_SHARE_NORMAL = 0.04     # share of regular sessions that are live sport
SPORT_SHARE_SPIKE = 0.40
SPIKE_MINUTES_BOOST = 1.3     # sports sessions are longer during the spike

RATE = {"Free": 1.0, "Mobile": 1.4, "Standard": 1.8, "Premium": 2.4}       # relative activity
TIER_MINUTES = {"Free": 0.85, "Mobile": 0.95, "Standard": 1.05, "Premium": 1.15}
MEAN_MIN = {"Movie": 75, "Series": 40, "Live Sport": 95}
SD_MIN = {"Movie": 25, "Series": 15, "Live Sport": 35}

users = pd.read_csv(DATA_DIR / "users.csv", parse_dates=["signup_date", "cancel_date"])
content = pd.read_csv(DATA_DIR / "content.csv")

# ---------- Each user's active window ----------
start = users["signup_date"].clip(lower=DATA_START)
end = users["cancel_date"].fillna(DATA_END).clip(upper=DATA_END)
span = ((end - start).dt.days + 1).clip(lower=0)

# ---------- How many regular sessions per user ----------
rate = users["subscription_tier"].map(RATE)
expected = rate * span / 30 * rng.gamma(2.0, 0.5, len(users))   # gamma = a few heavy viewers, many light
n_events = rng.poisson(expected * TARGET_BASE_ROWS / expected.sum())


def expand(user_ids, starts, spans, counts):
    """Create one row per session, with a random date inside each user's window."""
    uid = np.repeat(user_ids, counts)
    s = np.repeat(starts, counts)
    sp = np.repeat(spans, counts)
    offset = (rng.random(len(uid)) * sp).astype(int)
    dates = pd.to_datetime(s) + pd.to_timedelta(offset, unit="D")
    return pd.DataFrame({"user_id": uid, "watch_date": dates})


# ---------- Regular sessions ----------
base = expand(users["user_id"].to_numpy(), start.to_numpy(), span.to_numpy(), n_events)

# ---------- Extra cricket-spike sessions ----------
o_start = np.maximum(start.to_numpy(), SPIKE_START.to_datetime64())
o_end = np.minimum(end.to_numpy(), SPIKE_END.to_datetime64())
sp_span = np.clip((o_end - o_start).astype("timedelta64[D]").astype(int) + 1, 0, None)
extra_counts = np.where(sp_span > 0, rng.poisson(EXTRA_SPIKE_MEAN, len(users)), 0)
extra = expand(users["user_id"].to_numpy(), o_start, sp_span, extra_counts)

# ---------- Pick content ----------
ctype_map = content.set_index("content_id")["content_type"]
sport_ids = content.loc[content["content_type"] == "Live Sport", "content_id"].to_numpy()
regular_ids = rng.permutation(content.loc[content["content_type"] != "Live Sport", "content_id"].to_numpy())

popularity = 1 / np.arange(1, len(regular_ids) + 1) ** 0.8   # a few titles are very popular
popularity /= popularity.sum()

in_spike = base["watch_date"].between(SPIKE_START, SPIKE_END)
is_sport = rng.random(len(base)) < np.where(in_spike, SPORT_SHARE_SPIKE, SPORT_SHARE_NORMAL)
base["content_id"] = np.where(
    is_sport,
    rng.choice(sport_ids, len(base)),
    rng.choice(regular_ids, len(base), p=popularity),
)
extra["content_id"] = rng.choice(sport_ids, len(extra))

views = pd.concat([base, extra], ignore_index=True)

# ---------- Watch minutes and device ----------
views["content_type"] = views["content_id"].map(ctype_map)
tier_map = users.set_index("user_id")["subscription_tier"]
views["tier"] = views["user_id"].map(tier_map)

mean = views["content_type"].map(MEAN_MIN).to_numpy()
sd = views["content_type"].map(SD_MIN).to_numpy()
minutes = rng.normal(mean, sd) * views["tier"].map(TIER_MINUTES).to_numpy()

spike_sport = views["watch_date"].between(SPIKE_START, SPIKE_END) & (views["content_type"] == "Live Sport")
minutes = np.where(spike_sport, minutes * SPIKE_MINUTES_BOOST, minutes)
views["watch_minutes"] = np.clip(minutes, 5, 240).round().astype(int)

views["device"] = rng.choice(["Mobile", "Smart TV", "Laptop"], len(views), p=[0.60, 0.25, 0.15])

# ---------- Final table ----------
views = views.sort_values("watch_date").reset_index(drop=True)
views.insert(0, "view_id", views.index + 1)
out = views[["view_id", "user_id", "content_id", "watch_date", "watch_minutes", "device"]]
out.to_csv(DATA_DIR / "viewership.csv", index=False, date_format="%Y-%m-%d")

# ---------- Data-quality checks ----------
check = out.merge(users[["user_id", "signup_date", "cancel_date", "subscription_tier"]], on="user_id")
print("Viewership rows:", len(out))
print("Rows before signup (must be 0):", int((check["watch_date"] < check["signup_date"]).sum()))
print("Rows after cancel  (must be 0):", int((check["watch_date"] > check["cancel_date"]).sum()))

daily = out.groupby("watch_date")["watch_minutes"].sum()
spike_avg = daily[SPIKE_START:SPIKE_END].mean()
normal_avg = daily.drop(daily[SPIKE_START:SPIKE_END].index).mean()
print(f"\nAvg daily minutes, normal days: {normal_avg:,.0f}")
print(f"Avg daily minutes, spike window: {spike_avg:,.0f}  (x{spike_avg / normal_avg:.1f})")

print("\nAvg minutes per session by tier:")
print(check.groupby("subscription_tier")["watch_minutes"].mean().round(1))
print(daily["2025-04-01":"2025-05-05"])