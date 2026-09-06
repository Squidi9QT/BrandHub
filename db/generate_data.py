import random
from datetime import date, timedelta

import psycopg2
import psycopg2.extras

DB_NAME = "park_ads"
random.seed(42)

DATE_START = date(2026, 6, 1)
DATE_END = date(2026, 8, 31)

OPEN_HOUR, CLOSE_HOUR = 10, 21

WEEKEND_MULTIPLIER = 1.5

PEAK_OCCUPANCY_RATE = {
    "food_court":   0.60,
    "nursery":      0.50,
    "kids_zone":    0.55,
    "slides":       0.50,
    "trampolines":  0.50,
    "attractions":  0.45,
    "rest_area":    0.40,
}

ZONE_SEGMENT_MIX = {
    "food_court":  {"toddlers": 0.05, "kids": 0.20, "teens": 0.15, "adults": 0.45, "seniors": 0.15},
    "nursery":     {"toddlers": 0.55, "kids": 0.05, "adults": 0.40},
    "kids_zone":   {"toddlers": 0.15, "kids": 0.50, "teens": 0.05, "adults": 0.30},
    "slides":      {"toddlers": 0.05, "kids": 0.45, "teens": 0.35, "adults": 0.15},
    "trampolines": {"kids": 0.40, "teens": 0.45, "adults": 0.15},
    "attractions": {"adults": 0.75, "seniors": 0.25},
    "rest_area":   {"kids": 0.05, "teens": 0.05, "adults": 0.55, "seniors": 0.35},
}


def pulse(t, center, k):
    return max(0.0, 1.0 - abs(t - center) * k) ** 2


def hour_shape(zone_type, hour):
    t = (hour - OPEN_HOUR) / (CLOSE_HOUR - OPEN_HOUR)
    if zone_type == "food_court":
        return 0.9 * pulse(t, 0.25, 2.2) + 1.0 * pulse(t, 0.8, 2.2) + 0.15
    if zone_type == "nursery":
        return max(0.15, 1.0 - t * 0.9)
    if zone_type == "kids_zone":
        return 1.0 * pulse(t, 0.45, 1.6) + 0.2
    if zone_type in ("slides", "trampolines"):
        return 1.0 * pulse(t, 0.65, 1.5) + 0.2
    if zone_type == "attractions":
        return max(0.1, t ** 1.5)
    if zone_type == "rest_area":
        return 0.6 + 0.4 * pulse(t, 0.55, 1.3)
    return 0.5


DAILY_RATE = {
    "food_court": 15000, "nursery": 5000, "kids_zone": 10000,
    "slides": 8000, "trampolines": 8000, "attractions": 12000, "rest_area": 9000,
}

VISIBILITY_RATE = 0.65
CTR_MIN, CTR_MAX = 0.01, 0.06

PLACEMENTS = [
    ("Coca-Cola",    "Фудкорт",       date(2026, 6, 15), date(2026, 8, 15)),
    ("Coca-Cola",    "Зона батутов",  date(2026, 7, 1),  date(2026, 7, 31)),
    ("Coca-Cola",    "Ясли",          date(2026, 6, 1),  date(2026, 6, 30)),

    ("Lay's",        "Зона горок",    date(2026, 6, 1),  date(2026, 7, 15)),
    ("Lay's",        "Зона батутов",  date(2026, 7, 20), date(2026, 8, 20)),
    ("Lay's",        "Зона отдыха",   date(2026, 8, 1),  date(2026, 8, 31)),

    ("Snickers",     "Детская зона",  date(2026, 6, 10), date(2026, 7, 10)),
    ("Snickers",     "Фудкорт",       date(2026, 7, 15), date(2026, 8, 15)),
    ("Snickers",     "Ясли",          date(2026, 6, 1),  date(2026, 6, 20)),

    ("Air Astana",   "Зона отдыха",   date(2026, 6, 1),  date(2026, 7, 31)),
    ("Air Astana",   "Аттракционы",   date(2026, 8, 1),  date(2026, 8, 31)),
    ("Air Astana",   "Фудкорт",       date(2026, 6, 15), date(2026, 7, 15)),

    ("Freedom Bank", "Аттракционы",   date(2026, 7, 1),  date(2026, 8, 31)),
    ("Freedom Bank", "Зона отдыха",   date(2026, 6, 1),  date(2026, 6, 30)),
    ("Freedom Bank", "Фудкорт",       date(2026, 6, 1),  date(2026, 7, 31)),
]


def daterange(d1, d2):
    for n in range((d2 - d1).days + 1):
        yield d1 + timedelta(days=n)


def main():
    conn = psycopg2.connect(dbname=DB_NAME)
    cur = conn.cursor()

    cur.execute("DELETE FROM placement_metrics")
    cur.execute("DELETE FROM placements")
    cur.execute("DELETE FROM zone_traffic")
    conn.commit()

    cur.execute("SELECT id, name, zone_type, capacity FROM zones")
    zones = {row[1]: row for row in cur.fetchall()}

    cur.execute("SELECT id, name FROM audience_segments")
    segment_ids = {name: sid for sid, name in cur.fetchall()}

    cur.execute("SELECT id, name FROM brands")
    brand_ids = {name: bid for bid, name in cur.fetchall()}

    cur.execute("SELECT zone_type, restricted_category FROM zone_category_restrictions")
    restrictions = {(zt, cat) for zt, cat in cur.fetchall()}

    cur.execute("SELECT name, category FROM brands")
    brand_category = {name: cat for name, cat in cur.fetchall()}

    cur.execute("""
        SELECT b.name, s.name, bts.weight FROM brand_target_segments bts
        JOIN brands b ON b.id = bts.brand_id
        JOIN audience_segments s ON s.id = bts.segment_id
    """)
    target_weights = {}
    for bname, sname, w in cur.fetchall():
        target_weights.setdefault(bname, {})[sname] = float(w)

    traffic_rows = []
    daily_zone_segment = {}

    for zone_name, (zid, _, ztype, capacity) in zones.items():
        mix = ZONE_SEGMENT_MIX[ztype]
        for d in daterange(DATE_START, DATE_END):
            is_weekend = d.weekday() >= 5
            day_factor = WEEKEND_MULTIPLIER if is_weekend else 1.0
            daily_noise = random.uniform(0.85, 1.15)

            for hour in range(OPEN_HOUR, CLOSE_HOUR + 1):
                shape = hour_shape(ztype, hour)
                total = round(
                    capacity * PEAK_OCCUPANCY_RATE[ztype] * shape
                    * day_factor * daily_noise * random.uniform(0.9, 1.1)
                )
                if total <= 0:
                    continue

                seg_names = list(mix.keys())
                raw = [total * mix[s] for s in seg_names]
                counts = [int(x) for x in raw]
                remainder = total - sum(counts)
                fracs = sorted(range(len(seg_names)), key=lambda i: raw[i] - counts[i], reverse=True)
                for i in fracs[:remainder]:
                    counts[i] += 1

                key = (zone_name, d)
                daily_zone_segment.setdefault(key, {})
                for sname, cnt in zip(seg_names, counts):
                    if cnt <= 0:
                        continue
                    traffic_rows.append((zid, d, hour, segment_ids[sname], cnt))
                    daily_zone_segment[key][sname] = daily_zone_segment[key].get(sname, 0) + cnt

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO zone_traffic (zone_id, date, hour, segment_id, visitor_count) VALUES %s",
        traffic_rows,
        page_size=1000,
    )
    conn.commit()
    print(f"zone_traffic: вставлено {len(traffic_rows)} строк")

    placement_rows = []
    for brand, zone_name, start, end in PLACEMENTS:
        ztype = zones[zone_name][2]
        cat = brand_category[brand]
        assert (ztype, cat) not in restrictions, (
            f"НАРУШЕНИЕ ПРАВИЛА: {brand} ({cat}) нельзя размещать в '{zone_name}' ({ztype})"
        )
        duration_days = (end - start).days + 1
        cost_total = round(DAILY_RATE[ztype] * duration_days * random.uniform(0.95, 1.05))
        placement_rows.append((brand_ids[brand], zones[zone_name][0], start, end, cost_total))

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO placements (brand_id, zone_id, start_date, end_date, cost_total) VALUES %s",
        placement_rows,
    )
    conn.commit()
    print(f"placements: вставлено {len(placement_rows)} строк (все прошли проверку на restrictions)")

    metrics_rows = []
    cur.execute(
        "SELECT p.id, b.name, z.name, p.start_date, p.end_date, p.cost_total "
        "FROM placements p JOIN brands b ON b.id=p.brand_id JOIN zones z ON z.id=p.zone_id"
    )
    placement_ids = cur.fetchall()
    for pid, brand, zone_name, start, end, cost_total in placement_ids:
        cost_total = float(cost_total)
        d_start = max(start, DATE_START)
        d_end = min(end, DATE_END)
        duration_days = (end - start).days + 1
        daily_cost = cost_total / duration_days
        weights = target_weights.get(brand, {})

        for d in daterange(d_start, d_end):
            seg_counts = daily_zone_segment.get((zone_name, d), {})
            total_visitors = sum(seg_counts.values())
            if total_visitors == 0:
                continue

            reach_weight = sum(
                (cnt / total_visitors) * weights.get(seg, 0.0) for seg, cnt in seg_counts.items()
            )

            impressions = round(total_visitors * VISIBILITY_RATE)
            noise = random.uniform(0.9, 1.1)
            estimated_ctr = max(0.001, min(0.15, (CTR_MIN + reach_weight * (CTR_MAX - CTR_MIN)) * noise))
            estimated_responses = max(0, round(impressions * estimated_ctr))
            cost_per_contact = round(daily_cost / estimated_responses, 2) if estimated_responses > 0 else None

            metrics_rows.append((pid, d, impressions, round(estimated_ctr, 4),
                                  estimated_responses, cost_per_contact))

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO placement_metrics (placement_id, date, impressions, estimated_ctr, "
        "estimated_responses, cost_per_contact) VALUES %s",
        [r for r in metrics_rows if r[5] is not None],
        page_size=1000,
    )
    conn.commit()
    print(f"placement_metrics: вставлено {len([r for r in metrics_rows if r[5] is not None])} строк")

    conn.close()
    print("Готово.")


if __name__ == "__main__":
    main()
