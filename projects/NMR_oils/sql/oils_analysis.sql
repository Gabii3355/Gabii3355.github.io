-- MySQL analytical queries for the NMR oils database.
-- Each query starts with: -- name: query_name

-- name: samples_by_oil_type
SELECT oil_type,COUNT(*) AS number_of_samples
FROM samples
GROUP BY oil_type
ORDER BY number_of_samples DESC, oil_type;


-- name: intensity_by_oil_type
SELECT
    samples.oil_type,
    nmr_measurements.chemical_shift_ppm,
    ROUND(AVG(nmr_measurements.intensity), 2) AS mean_intensity,
    ROUND(MIN(nmr_measurements.intensity), 2) AS min_intensity,
    ROUND(MAX(nmr_measurements.intensity), 2) AS max_intensity,
    COUNT(nmr_measurements.intensity) AS available_measurements
FROM samples
INNER JOIN nmr_measurements
    ON samples.sample_id = nmr_measurements.sample_id
GROUP BY
    samples.oil_type,
    nmr_measurements.chemical_shift_ppm
ORDER BY
    nmr_measurements.chemical_shift_ppm,
    mean_intensity DESC;


-- name: strongest_nmr_signals
SELECT
    samples.oil_type,
    nmr_measurements.chemical_shift_ppm,
    ROUND(AVG(nmr_measurements.intensity), 2) AS mean_intensity
FROM samples
JOIN nmr_measurements
    ON samples.sample_id = nmr_measurements.sample_id
GROUP BY
    samples.oil_type,
    nmr_measurements.chemical_shift_ppm
ORDER BY mean_intensity DESC
LIMIT 10;

-- name: ranked_signals_by_oil_type
WITH mean_signals AS (
    SELECT
        samples.oil_type,
        nmr_measurements.chemical_shift_ppm,
        AVG(nmr_measurements.intensity) AS mean_intensity
    FROM samples
    INNER JOIN nmr_measurements
        ON samples.sample_id = nmr_measurements.sample_id
    WHERE nmr_measurements.intensity IS NOT NULL
    GROUP BY
        samples.oil_type,
        nmr_measurements.chemical_shift_ppm
)

SELECT
    mean_signals.oil_type,
    mean_signals.chemical_shift_ppm,
    ROUND(mean_signals.mean_intensity, 2) AS mean_intensity,
    RANK() OVER (
        PARTITION BY mean_signals.oil_type
        ORDER BY mean_signals.mean_intensity DESC
    ) AS signal_rank
FROM mean_signals
ORDER BY
    mean_signals.oil_type,
    signal_rank,
    mean_signals.chemical_shift_ppm;

-- name: measurements_by_manufacturer
SELECT
    manufacturer,
    COUNT(DISTINCT sample_id) AS number_of_samples
FROM samples
GROUP BY manufacturer
ORDER BY number_of_samples DESC, manufacturer;
