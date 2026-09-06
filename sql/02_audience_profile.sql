SELECT
    z.name AS zone,
    z.zone_type,
    s.name AS segment,
    SUM(zt.visitor_count) AS visitors,
    ROUND(
        100.0 * SUM(zt.visitor_count) / SUM(SUM(zt.visitor_count)) OVER (PARTITION BY z.id),
        1
    ) AS pct_of_zone_traffic
FROM zone_traffic zt
JOIN zones z ON z.id = zt.zone_id
JOIN audience_segments s ON s.id = zt.segment_id
GROUP BY z.id, s.id
ORDER BY z.name, pct_of_zone_traffic DESC;
