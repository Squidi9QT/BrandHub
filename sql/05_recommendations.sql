WITH zone_segment_totals AS (
    SELECT z.id AS zone_id, z.name AS zone_name, z.zone_type, s.id AS segment_id,
           SUM(zt.visitor_count) AS visitors
    FROM zone_traffic zt
    JOIN zones z ON z.id = zt.zone_id
    JOIN audience_segments s ON s.id = zt.segment_id
    GROUP BY z.id, s.id
),
zone_mix AS (
    SELECT zst.zone_id, zst.zone_name, zst.zone_type, zst.segment_id,
           zst.visitors * 1.0 / SUM(zst.visitors) OVER (PARTITION BY zst.zone_id) AS share
    FROM zone_segment_totals zst
),
brand_zone_scores AS (
    SELECT b.id AS brand_id, b.name AS brand, b.category,
           zm.zone_id, zm.zone_name AS zone,
           SUM(zm.share * COALESCE(bts.weight, 0)) AS match_score
    FROM brands b
    CROSS JOIN zone_mix zm
    LEFT JOIN brand_target_segments bts
        ON bts.brand_id = b.id AND bts.segment_id = zm.segment_id
    LEFT JOIN zone_category_restrictions r
        ON r.zone_type = zm.zone_type AND r.restricted_category = b.category
    WHERE r.id IS NULL
    GROUP BY b.id, b.name, b.category, zm.zone_id, zm.zone_name
),
best_zone_per_brand AS (
    SELECT brand_id, zone AS best_zone, match_score AS best_score,
           RANK() OVER (PARTITION BY brand_id ORDER BY match_score DESC) AS rnk
    FROM brand_zone_scores
),
current_placements AS (
    SELECT p.id AS placement_id, b.id AS brand_id, b.name AS brand,
           z.id AS zone_id, z.name AS current_zone,
           p.cost_total, p.start_date, p.end_date
    FROM placements p
    JOIN brands b ON b.id = p.brand_id
    JOIN zones z ON z.id = p.zone_id
),
actual_perf AS (
    SELECT placement_id, ROUND(AVG(estimated_ctr), 4) AS actual_avg_ctr
    FROM placement_metrics
    GROUP BY placement_id
)
SELECT
    cp.brand,
    cp.current_zone,
    ROUND(bzs.match_score, 4) AS current_zone_match_score,
    ap.actual_avg_ctr,
    bp.best_zone AS recommended_zone,
    ROUND(bp.best_score, 4) AS recommended_zone_match_score,
    ROUND((bp.best_score - bzs.match_score) / NULLIF(bzs.match_score, 0) * 100, 1) AS potential_uplift_pct,
    cp.start_date,
    cp.end_date,
    cp.cost_total
FROM current_placements cp
JOIN brand_zone_scores bzs ON bzs.brand_id = cp.brand_id AND bzs.zone_id = cp.zone_id
JOIN best_zone_per_brand bp ON bp.brand_id = cp.brand_id AND bp.rnk = 1
LEFT JOIN actual_perf ap ON ap.placement_id = cp.placement_id
WHERE bzs.match_score < bp.best_score * 0.9
  AND cp.current_zone != bp.best_zone
ORDER BY potential_uplift_pct DESC;
