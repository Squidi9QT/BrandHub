CREATE TABLE zones (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                    TEXT NOT NULL UNIQUE,
    zone_type               TEXT NOT NULL,
    avg_dwell_time_minutes  INTEGER NOT NULL,
    capacity                INTEGER NOT NULL,
    min_visitor_age         INTEGER
);

CREATE TABLE audience_segments (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    age_range   TEXT NOT NULL,
    min_age     INTEGER NOT NULL,
    max_age     INTEGER
);

CREATE TABLE zone_traffic (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    zone_id         INTEGER NOT NULL REFERENCES zones(id),
    date            DATE NOT NULL,
    hour            INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    segment_id      INTEGER NOT NULL REFERENCES audience_segments(id),
    visitor_count   INTEGER NOT NULL CHECK (visitor_count >= 0)
);

CREATE INDEX idx_zone_traffic_zone_date ON zone_traffic(zone_id, date);
CREATE INDEX idx_zone_traffic_segment ON zone_traffic(segment_id);

CREATE TABLE brands (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                TEXT NOT NULL UNIQUE,
    category            TEXT NOT NULL,
    campaign_budget     NUMERIC(14,2) NOT NULL CHECK (campaign_budget >= 0)
);

CREATE TABLE brand_target_segments (
    brand_id    INTEGER NOT NULL REFERENCES brands(id),
    segment_id  INTEGER NOT NULL REFERENCES audience_segments(id),
    weight      NUMERIC(5,4) NOT NULL CHECK (weight BETWEEN 0 AND 1),
    PRIMARY KEY (brand_id, segment_id)
);

CREATE TABLE placements (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    brand_id    INTEGER NOT NULL REFERENCES brands(id),
    zone_id     INTEGER NOT NULL REFERENCES zones(id),
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    cost_total  NUMERIC(14,2) NOT NULL CHECK (cost_total >= 0),
    CHECK (end_date >= start_date)
);

CREATE INDEX idx_placements_brand ON placements(brand_id);
CREATE INDEX idx_placements_zone ON placements(zone_id);

CREATE TABLE placement_metrics (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    placement_id        INTEGER NOT NULL REFERENCES placements(id),
    date                DATE NOT NULL,
    impressions         INTEGER NOT NULL CHECK (impressions >= 0),
    estimated_ctr       NUMERIC(6,4) NOT NULL CHECK (estimated_ctr >= 0),
    estimated_responses INTEGER NOT NULL CHECK (estimated_responses >= 0),
    cost_per_contact    NUMERIC(14,2) NOT NULL CHECK (cost_per_contact >= 0)
);

CREATE INDEX idx_placement_metrics_placement ON placement_metrics(placement_id, date);

CREATE TABLE zone_category_restrictions (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    zone_type           TEXT NOT NULL,
    restricted_category TEXT NOT NULL,
    reason              TEXT NOT NULL,
    UNIQUE (zone_type, restricted_category)
);
