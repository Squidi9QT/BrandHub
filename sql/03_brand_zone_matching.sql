WITH zone_segment_totals AS (
    SELECT
        z.id AS zone_id, z.name AS zone_name, z.zone_type,
        s.id AS segment_id,
        SUM(zt.visitor_count) AS visitors
    FROM zone_traffic zt
    JOIN zones z ON z.id = zt.zone_id
    JOIN audience_segments s ON s.id = zt.segment_id
    GROUP BY z.id, s.id
),
zone_mix AS (
    SELECT
        zst.zone_id, zst.zone_name, zst.zone_type, zst.segment_id,
        zst.visitors * 1.0 / SUM(zst.visitors) OVER (PARTITION BY zst.zone_id) AS share
    FROM zone_segment_totals zst
)
SELECT
    b.name AS brand,
    b.category,
    zm.zone_name AS zone,
    ROUND(SUM(zm.share * COALESCE(bts.weight, 0)), 4) AS match_score,
    RANK() OVER (PARTITION BY b.id ORDER BY SUM(zm.share * COALESCE(bts.weight, 0)) DESC) AS rank_for_brand
FROM brands b
CROSS JOIN zone_mix zm
LEFT JOIN brand_target_segments bts
    ON bts.brand_id = b.id AND bts.segment_id = zm.segment_id
LEFT JOIN zone_category_restrictions r
    ON r.zone_type = zm.zone_type AND r.restricted_category = b.category
WHERE r.id IS NULL
GROUP BY b.id, b.name, b.category, zm.zone_id, zm.zone_name
ORDER BY b.name, match_score DESC;
