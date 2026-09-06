SELECT
    p.id AS placement_id,
    b.name AS brand,
    z.name AS zone,
    p.start_date,
    p.end_date,
    p.cost_total,
    SUM(pm.impressions) AS total_impressions,
    SUM(pm.estimated_responses) AS total_target_contacts,
    ROUND(AVG(pm.estimated_ctr), 4) AS avg_ctr,
    ROUND(p.cost_total * 1000.0 / NULLIF(SUM(pm.impressions), 0), 1) AS cpm,
    ROUND(p.cost_total * 1.0 / NULLIF(SUM(pm.estimated_responses), 0), 1) AS cost_per_target_contact,
    RANK() OVER (
        PARTITION BY b.name
        ORDER BY p.cost_total * 1.0 / NULLIF(SUM(pm.estimated_responses), 0) ASC
    ) AS efficiency_rank_within_brand
FROM placements p
JOIN brands b ON b.id = p.brand_id
JOIN zones z ON z.id = p.zone_id
JOIN placement_metrics pm ON pm.placement_id = p.id
GROUP BY p.id, b.name, z.name
ORDER BY b.name, cost_per_target_contact ASC;
