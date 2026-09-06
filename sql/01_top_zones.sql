WITH zone_traffic_totals AS (
    SELECT
        z.id,
        z.name,
        z.zone_type,
        z.avg_dwell_time_minutes,
        z.capacity,
        SUM(zt.visitor_count) AS total_visitors,
        ROUND(SUM(zt.visitor_count) * 1.0 / COUNT(DISTINCT zt.date)) AS avg_daily_visitors
    FROM zones z
    JOIN zone_traffic zt ON zt.zone_id = z.id
    GROUP BY z.id
)
SELECT
    name AS zone,
    zone_type,
    total_visitors,
    avg_daily_visitors,
    avg_dwell_time_minutes AS dwell_min,
    ROUND(total_visitors * avg_dwell_time_minutes / 1000.0, 1) AS exposure_score_k_person_min,
    RANK() OVER (ORDER BY total_visitors DESC) AS rank_by_traffic,
    RANK() OVER (ORDER BY avg_dwell_time_minutes DESC) AS rank_by_dwell,
    RANK() OVER (ORDER BY total_visitors * avg_dwell_time_minutes DESC) AS rank_by_exposure
FROM zone_traffic_totals
ORDER BY exposure_score_k_person_min DESC;
