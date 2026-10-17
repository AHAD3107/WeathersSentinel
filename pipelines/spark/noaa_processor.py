from pathlib import Path

from pyspark.sql import SparkSession

from pyspark.sql.functions import (

    avg,

    col,

    concat_ws,

    count,

    desc,

    lpad,

    lit,

    max as spark_max,

    min as spark_min,

    stddev,

    to_date,

    to_timestamp,

    when,

)

from pyspark.sql.types import (

    IntegerType,

    StructField,

    StructType,

)

# ============================================================

# PROJECT PATHS

# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = (

    PROJECT_ROOT

    / "data"

    / "raw"

    / "pune_43063_2024"

)

PROCESSED_ROOT = (

    PROJECT_ROOT

    / "data"

    / "processed"

    / "noaa"

)

OBSERVATIONS_OUTPUT = (

    PROCESSED_ROOT

    / "observations"

)

DAILY_OUTPUT = (

    PROCESSED_ROOT

    / "daily"

)

# ============================================================

# SPARK SESSION

# ============================================================

spark = (

    SparkSession.builder

    .appName(

        "WeatherSentinel-NOAA-Processor"

    )

    .master("local[*]")

    # Windows localhost configuration

    .config(

        "spark.driver.host",

        "127.0.0.1",

    )

    .config(

        "spark.driver.bindAddress",

        "127.0.0.1",

    )

    # Keep Hadoop's normal LocalFileSystem.

    # Do NOT replace it with RawLocalFileSystem.

    .config(

        "spark.hadoop.fs.file.impl",

        "org.apache.hadoop.fs.LocalFileSystem",

    )

    # Prevent Hadoop from attempting POSIX-style

    # permission changes on Windows.

    .config(

        "spark.hadoop.fs.permissions.umask-mode",

        "000",

    )

    .getOrCreate()

)

spark.sparkContext.setLogLevel("WARN")

# ============================================================

# NOAA ISD-LITE SCHEMA

# ============================================================

schema = StructType(

    [

        StructField(

            "year",

            IntegerType(),

            True,

        ),

        StructField(

            "month",

            IntegerType(),

            True,

        ),

        StructField(

            "day",

            IntegerType(),

            True,

        ),

        StructField(

            "hour",

            IntegerType(),

            True,

        ),

        StructField(

            "air_temperature",

            IntegerType(),

            True,

        ),

        StructField(

            "dew_point_temperature",

            IntegerType(),

            True,

        ),

        StructField(

            "sea_level_pressure",

            IntegerType(),

            True,

        ),

        StructField(

            "wind_direction",

            IntegerType(),

            True,

        ),

        StructField(

            "wind_speed",

            IntegerType(),

            True,

        ),

        StructField(

            "cloud_cover",

            IntegerType(),

            True,

        ),

        StructField(

            "one_hour_precipitation",

            IntegerType(),

            True,

        ),

        StructField(

            "six_hour_precipitation",

            IntegerType(),

            True,

        ),

    ]

)

# ============================================================

# START

# ============================================================

print("=" * 70)

print(

    "WeatherSentinel - NOAA ISD-Lite "

    "PySpark Processor"

)

print("=" * 70)

print("\nReading NOAA file:")

print(RAW_FILE)

# ============================================================

# READ RAW NOAA FILE

# ============================================================

raw_rdd = spark.sparkContext.textFile(

    str(RAW_FILE)

)

raw_line_count = raw_rdd.count()

print(

    f"\nRaw records: {raw_line_count}"

)

# ============================================================

# PARSE NOAA RECORD

# ============================================================

def parse_noaa_line(line):

    parts = line.split()

    if len(parts) != 12:

        return None

    try:

        return tuple(

            int(value)

            for value in parts

        )

    except ValueError:

        return None

rows_rdd = (

    raw_rdd

    .map(parse_noaa_line)

    .filter(

        lambda x: x is not None

    )

)

parsed_count = rows_rdd.count()

print(

    "Successfully parsed records: "

    f"{parsed_count}"

)

# ============================================================

# CREATE DATAFRAME

# ============================================================

df = spark.createDataFrame(

    rows_rdd,

    schema=schema,

)

# ============================================================

# HANDLE NOAA MISSING VALUES

# ============================================================

missing_value_columns = [

    "air_temperature",

    "dew_point_temperature",

    "sea_level_pressure",

    "wind_direction",

    "wind_speed",

    "cloud_cover",

    "one_hour_precipitation",

    "six_hour_precipitation",

]

for column_name in missing_value_columns:

    df = df.withColumn(

        column_name,

        when(

            col(column_name) == -9999,

            None,

        ).otherwise(

            col(column_name)

        ),

    )

# ============================================================

# UNIT CONVERSION

# ============================================================

df = (

    df

    # Temperature -> Celsius

    .withColumn(

        "temperature_c",

        col("air_temperature")

        / lit(10.0),

    )

    # Dew point -> Celsius

    .withColumn(

        "dew_point_c",

        col("dew_point_temperature")

        / lit(10.0),

    )

    # Pressure -> hPa

    .withColumn(

        "pressure_hpa",

        col("sea_level_pressure")

        / lit(10.0),

    )

    # Wind speed -> m/s

    .withColumn(

        "wind_speed_ms",

        col("wind_speed")

        / lit(10.0),

    )

    # Precipitation -> mm

    .withColumn(

        "rainfall_1h_mm",

        col("one_hour_precipitation")

        / lit(10.0),

    )

    .withColumn(

        "rainfall_6h_mm",

        col("six_hour_precipitation")

        / lit(10.0),

    )

)

# ============================================================

# TRACE PRECIPITATION

# ============================================================

# NOAA uses -1 to represent trace precipitation.

#

# Trace precipitation is represented as 0.0

# for this processing pipeline.

df = (

    df

    .withColumn(

        "rainfall_1h_mm",

        when(

            col("one_hour_precipitation")

            == -1,

            lit(0.0),

        ).otherwise(

            col("rainfall_1h_mm")

        ),

    )

    .withColumn(

        "rainfall_6h_mm",

        when(

            col("six_hour_precipitation")

            == -1,

            lit(0.0),

        ).otherwise(

            col("rainfall_6h_mm")

        ),

    )

)

# ============================================================

# BUILD OBSERVATION TIMESTAMP

# ============================================================

df = df.withColumn(

    "observed_at",

    to_timestamp(

        concat_ws(

            " ",

            concat_ws(

                "-",

                col("year"),

                lpad(

                    col("month"),

                    2,

                    "0",

                ),

                lpad(

                    col("day"),

                    2,

                    "0",

                ),

            ),

            concat_ws(

                ":",

                lpad(

                    col("hour"),

                    2,

                    "0",

                ),

                lit("00"),

                lit("00"),

            ),

        ),

        "yyyy-MM-dd HH:mm:ss",

    ),

)

# ============================================================

# DATA QUALITY VALIDATION

# ============================================================

df = (

    df

    # Temperature

    .withColumn(

        "temperature_valid",

        (

            col("temperature_c").isNull()

            |

            (

                (col("temperature_c") >= -80)

                &

                (col("temperature_c") <= 60)

            )

        ),

    )

    # Pressure

    .withColumn(

        "pressure_valid",

        (

            col("pressure_hpa").isNull()

            |

            (

                (col("pressure_hpa") >= 800)

                &

                (col("pressure_hpa") <= 1100)

            )

        ),

    )

    # Wind speed

    .withColumn(

        "wind_speed_valid",

        (

            col("wind_speed_ms").isNull()

            |

            (

                col("wind_speed_ms") >= 0

            )

        ),

    )

    # Wind direction

    .withColumn(

        "wind_direction_valid",

        (

            col("wind_direction").isNull()

            |

            (

                (col("wind_direction") >= 0)

                &

                (col("wind_direction") <= 360)

            )

        ),

    )

    # Rainfall

    .withColumn(

        "rainfall_valid",

        (

            col("rainfall_1h_mm").isNull()

            |

            (

                col("rainfall_1h_mm") >= 0

            )

        ),

    )

)

# ============================================================

# RECORD VALIDITY

# ============================================================

# Precipitation is optional in this dataset.

#

# Missing precipitation therefore does NOT invalidate

# the weather observation.

df = df.withColumn(

    "record_valid",

    (

        col("temperature_valid")

        &

        col("pressure_valid")

        &

        col("wind_speed_valid")

        &

        col("wind_direction_valid")

    ),

)

# ============================================================

# DATA QUALITY SUMMARY

# ============================================================

total_records = df.count()

valid_records = (

    df

    .filter(

        col("record_valid")

    )

    .count()

)

invalid_records = (

    df

    .filter(

        ~col("record_valid")

    )

    .count()

)

missing_temperature = (

    df

    .filter(

        col("temperature_c").isNull()

    )

    .count()

)

missing_pressure = (

    df

    .filter(

        col("pressure_hpa").isNull()

    )

    .count()

)

missing_wind_speed = (

    df

    .filter(

        col("wind_speed_ms").isNull()

    )

    .count()

)

missing_wind_direction = (

    df

    .filter(

        col("wind_direction").isNull()

    )

    .count()

)

missing_1h_precipitation = (

    df

    .filter(

        col("rainfall_1h_mm").isNull()

    )

    .count()

)

missing_6h_precipitation = (

    df

    .filter(

        col("rainfall_6h_mm").isNull()

    )

    .count()

)

rainfall_failures = (

    df

    .filter(

        ~col("rainfall_valid")

    )

    .count()

)

# ============================================================

# PRINT DATA QUALITY

# ============================================================

print("\n" + "=" * 70)

print("DATA QUALITY")

print("=" * 70)

print(

    f"Total records:              "

    f"{total_records}"

)

print(

    f"Valid records:              "

    f"{valid_records}"

)

print(

    f"Invalid records:            "

    f"{invalid_records}"

)

print(

    f"Missing temperature:        "

    f"{missing_temperature}"

)

print(

    f"Missing pressure:           "

    f"{missing_pressure}"

)

print(

    f"Missing wind speed:         "

    f"{missing_wind_speed}"

)

print(

    f"Missing wind direction:     "

    f"{missing_wind_direction}"

)

print(

    f"Missing 1h precipitation:   "

    f"{missing_1h_precipitation}"

)

print(

    f"Missing 6h precipitation:   "

    f"{missing_6h_precipitation}"

)

print(

    f"Rainfall validation flags:  "

    f"{rainfall_failures}"

)

# ============================================================

# CREATE CLEAN OBSERVATION DATASET

# ============================================================

clean_df = (

    df

    .filter(

        col("record_valid")

    )

    .select(

        "year",

        "month",

        "day",

        "hour",

        "observed_at",

        "temperature_c",

        "dew_point_c",

        "pressure_hpa",

        "wind_direction",

        "wind_speed_ms",

        "cloud_cover",

        "rainfall_1h_mm",

        "rainfall_6h_mm",

        "record_valid",

    )

)

# ============================================================

# CREATE OUTPUT DIRECTORIES

# ============================================================

OBSERVATIONS_OUTPUT.mkdir(

    parents=True,

    exist_ok=True,

)

DAILY_OUTPUT.mkdir(

    parents=True,

    exist_ok=True,

)

# ============================================================

# PERSIST CLEAN OBSERVATIONS

# ============================================================

print("\n" + "=" * 70)

print(

    "PERSISTING PROCESSED "

    "OBSERVATIONS"

)

print("=" * 70)

clean_df.write \
    .mode("overwrite") \
    .parquet(

        str(OBSERVATIONS_OUTPUT)

    )

print(

    "Processed observations saved to:"

)

print(

    OBSERVATIONS_OUTPUT

)

# ============================================================

# DAILY AGGREGATION

# ============================================================

daily_df = (

    clean_df

    .withColumn(

        "date",

        to_date(

            col("observed_at")

        ),

    )

    .groupBy(

        "date"

    )

    .agg(

        count("*").alias(

            "observation_count"

        ),

        spark_min(

            "temperature_c"

        ).alias(

            "min_temperature_c"

        ),

        spark_max(

            "temperature_c"

        ).alias(

            "max_temperature_c"

        ),

        avg(

            "temperature_c"

        ).alias(

            "avg_temperature_c"

        ),

        avg(

            "pressure_hpa"

        ).alias(

            "avg_pressure_hpa"

        ),

        spark_min(

            "pressure_hpa"

        ).alias(

            "min_pressure_hpa"

        ),

        spark_max(

            "pressure_hpa"

        ).alias(

            "max_pressure_hpa"

        ),

        avg(

            "wind_speed_ms"

        ).alias(

            "avg_wind_speed_ms"

        ),

        spark_max(

            "wind_speed_ms"

        ).alias(

            "max_wind_speed_ms"

        ),

        avg(

            "wind_direction"

        ).alias(

            "avg_wind_direction"

        ),

        count(

            when(

                col(

                    "rainfall_1h_mm"

                ).isNotNull(),

                True,

            )

        ).alias(

            "rainfall_observations"

        ),

    )

    .orderBy(

        "date"

    )

)

# ============================================================

# PERSIST DAILY AGGREGATION

# ============================================================

print("\n" + "=" * 70)

print(

    "PERSISTING DAILY "

    "AGGREGATION"

)

print("=" * 70)

daily_df.write \
    .mode("overwrite") \
    .parquet(

        str(DAILY_OUTPUT)

    )

print(

    "Daily aggregates saved to:"

)

print(

    DAILY_OUTPUT

)

# ============================================================

# DAILY RECORD COUNT

# ============================================================

daily_count = daily_df.count()

print(

    f"\nDaily records generated: "

    f"{daily_count}"

)

# ============================================================

# DISPLAY DAILY DATA

# ============================================================

print("\n" + "=" * 70)

print(

    "DAILY WEATHER AGGREGATION"

)

print("=" * 70)

daily_df.show(

    10,

    truncate=False,

)

# ============================================================

# HOTTEST DAYS

# ============================================================

print("\n" + "=" * 70)

print("HOTTEST DAYS")

print("=" * 70)

(

    daily_df

    .select(

        "date",

        "max_temperature_c",

        "avg_temperature_c",

    )

    .orderBy(

        desc(

            "max_temperature_c"

        )

    )

    .show(

        10,

        truncate=False,

    )

)

# ============================================================

# STRONGEST WIND DAYS

# ============================================================

print("\n" + "=" * 70)

print("STRONGEST WIND DAYS")

print("=" * 70)

(

    daily_df

    .select(

        "date",

        "max_wind_speed_ms",

        "avg_wind_speed_ms",

    )

    .orderBy(

        desc(

            "max_wind_speed_ms"

        )

    )

    .show(

        10,

        truncate=False,

    )

)

# ============================================================

# LOWEST PRESSURE DAYS

# ============================================================

print("\n" + "=" * 70)

print("LOWEST PRESSURE DAYS")

print("=" * 70)

(

    daily_df

    .select(

        "date",

        "min_pressure_hpa",

        "avg_pressure_hpa",

    )

    .orderBy(

        "min_pressure_hpa"

    )

    .show(

        10,

        truncate=False,

    )

)

# ============================================================

# OVERALL TEMPERATURE STATISTICS

# ============================================================

print("\n" + "=" * 70)

print(

    "OVERALL TEMPERATURE "

    "STATISTICS"

)

print("=" * 70)

temperature_stats = (

    clean_df

    .select(

        count(

            "temperature_c"

        ).alias(

            "count"

        ),

        avg(

            "temperature_c"

        ).alias(

            "mean"

        ),

        stddev(

            "temperature_c"

        ).alias(

            "stddev"

        ),

        spark_min(

            "temperature_c"

        ).alias(

            "min"

        ),

        spark_max(

            "temperature_c"

        ).alias(

            "max"

        ),

    )

)

temperature_stats.show(

    truncate=False,

)

# ============================================================

# VERIFY PERSISTED PARQUET DATA

# ============================================================

print("\n" + "=" * 70)

print("VERIFYING PERSISTED DATA")

print("=" * 70)

saved_observations_df = (

    spark.read.parquet(

        str(

            OBSERVATIONS_OUTPUT

        )

    )

)

saved_daily_df = (

    spark.read.parquet(

        str(

            DAILY_OUTPUT

        )

    )

)

saved_observation_count = (

    saved_observations_df.count()

)

saved_daily_count = (

    saved_daily_df.count()

)

print(

    f"Saved observations: "

    f"{saved_observation_count}"

)

print(

    f"Saved daily records: "

    f"{saved_daily_count}"

)

# ============================================================

# FINAL VALIDATION

# ============================================================

if (

    saved_observation_count

    == valid_records

    and

    saved_daily_count

    == daily_count

):

    print("\n" + "=" * 70)

    print("STATUS: SUCCESS")

    print("=" * 70)

    print(

        "All NOAA observations passed "

        "core validation."

    )

    print(

        "Daily weather aggregation "

        "completed successfully."

    )

    print(

        "Processed Parquet datasets "

        "verified successfully."

    )

else:

    print("\n" + "=" * 70)

    print("STATUS: FAILURE")

    print("=" * 70)

    print(

        "Persisted record counts do not "

        "match the in-memory results."

    )

# ============================================================

# STOP SPARK

# ============================================================

spark.stop()
