INSERT INTO audience_segments (name, age_range, min_age, max_age) VALUES
    ('toddlers', '0-3',  0,  3),
    ('kids',     '4-11', 4,  11),
    ('teens',    '12-15', 12, 15),
    ('adults',   '16-59', 16, 59),
    ('seniors',  '60+',  60, NULL);

INSERT INTO zones (name, zone_type, avg_dwell_time_minutes, capacity, min_visitor_age) VALUES
    ('Фудкорт',        'food_court',   35, 300, NULL),
    ('Ясли',           'nursery',      50, 40,  NULL),
    ('Детская зона',   'kids_zone',    45, 60,  NULL),
    ('Зона горок',     'slides',       25, 50,  NULL),
    ('Зона батутов',   'trampolines',  30, 40,  NULL),
    ('Аттракционы',    'attractions',  20, 80,  16),
    ('Зона отдыха',    'rest_area',    40, 100, NULL);

INSERT INTO brands (name, category, campaign_budget) VALUES
    ('Coca-Cola',     'beverages', 1500000),
    ('Lay''s',        'snacks',     900000),
    ('Snickers',      'snacks',    1200000),
    ('Air Astana',    'airline',   3000000),
    ('Freedom Bank',  'banking',   2000000);

INSERT INTO brand_target_segments (brand_id, segment_id, weight)
SELECT b.id, s.id, w FROM brands b, audience_segments s,
    (SELECT 'Coca-Cola' AS brand, 'toddlers' AS seg, 0.05 AS w UNION ALL
     SELECT 'Coca-Cola', 'kids',    0.60 UNION ALL
     SELECT 'Coca-Cola', 'teens',   0.66 UNION ALL
     SELECT 'Coca-Cola', 'adults',  0.72 UNION ALL
     SELECT 'Coca-Cola', 'seniors', 0.33 UNION ALL

     SELECT 'Lay''s',    'toddlers', 0.05 UNION ALL
     SELECT 'Lay''s',    'kids',     0.70 UNION ALL
     SELECT 'Lay''s',    'teens',    0.90 UNION ALL
     SELECT 'Lay''s',    'adults',   0.50 UNION ALL
     SELECT 'Lay''s',    'seniors',  0.20 UNION ALL

     SELECT 'Snickers',  'toddlers', 0.05 UNION ALL
     SELECT 'Snickers',  'kids',     0.80 UNION ALL
     SELECT 'Snickers',  'teens',    0.48 UNION ALL
     SELECT 'Snickers',  'adults',   0.70 UNION ALL
     SELECT 'Snickers',  'seniors',  0.28 UNION ALL

     SELECT 'Air Astana', 'toddlers', 0.00 UNION ALL
     SELECT 'Air Astana', 'kids',     0.00 UNION ALL
     SELECT 'Air Astana', 'teens',    0.10 UNION ALL
     SELECT 'Air Astana', 'adults',   0.65 UNION ALL
     SELECT 'Air Astana', 'seniors',  0.70 UNION ALL

     SELECT 'Freedom Bank', 'toddlers', 0.00 UNION ALL
     SELECT 'Freedom Bank', 'kids',     0.00 UNION ALL
     SELECT 'Freedom Bank', 'teens',    0.05 UNION ALL
     SELECT 'Freedom Bank', 'adults',   0.70 UNION ALL
     SELECT 'Freedom Bank', 'seniors',  0.75
    ) t
WHERE b.name = t.brand AND s.name = t.seg AND w > 0;

INSERT INTO zone_category_restrictions (zone_type, restricted_category, reason) VALUES
    ('nursery',      'banking', 'Родитель занят уходом за малышом 0-3 лет, не в состоянии рассматривать финансовый продукт; репутационный риск соседства с яслями'),
    ('nursery',      'airline', 'Аудитория зоны не в контексте принятия решения о покупке авиабилета'),
    ('kids_zone',    'banking', 'Родитель занят присмотром за ребёнком, не фокусируется на рекламе финансовых услуг'),
    ('kids_zone',    'airline', 'Контекст зоны не располагает к решению о travel-покупке'),
    ('slides',       'banking', 'Высокая физическая активность и присмотр за ребёнком - не время для финансовых решений'),
    ('slides',       'airline', 'Высокая физическая активность - не время для travel-решений'),
    ('trampolines',  'banking', 'Высокая физическая активность и присмотр за ребёнком - не время для финансовых решений'),
    ('trampolines',  'airline', 'Высокая физическая активность - не время для travel-решений');
