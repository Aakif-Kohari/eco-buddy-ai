import os

base_dir = r"F:\ECSoC'26 Contributions\eco-buddy-ai"
datasets_file = os.path.join(base_dir, "environmental_benchmarking", "datasets.py")

with open(datasets_file, "r") as f:
    content = f.read()

# We'll inject before the final '}'
countries_data = """
    "ES": {
        "name": "Spain", "region": "Europe",
        "transport": {"mean": 1700, "median": 1400, "std_dev": 1000, "min_val": 0, "max_val": 9000, "p10": 300, "p25": 700, "p75": 2300, "p90": 3200},
        "electricity": {"mean": 2800, "median": 2500, "std_dev": 1200, "min_val": 0, "max_val": 9000, "p10": 900, "p25": 1600, "p75": 3500, "p90": 4500},
        "diet": {"mean": 1800, "median": 1700, "std_dev": 600, "min_val": 700, "max_val": 4800, "p10": 950, "p25": 1350, "p75": 2200, "p90": 2700},
        "flights": {"mean": 1.4, "median": 1, "std_dev": 2.1, "min_val": 0, "max_val": 30, "p10": 0, "p25": 0, "p75": 2, "p90": 4},
        "footprint": {"mean": 5200, "median": 4800, "std_dev": 2300, "min_val": 1400, "max_val": 18000, "p10": 2100, "p25": 3300, "p75": 6500, "p90": 8500},
        "eco_score": {"mean": 64, "median": 64, "std_dev": 14, "min_val": 0, "max_val": 100, "p10": 40, "p25": 52, "p75": 76, "p90": 86}
    },
    "IT": {
        "name": "Italy", "region": "Europe",
        "transport": {"mean": 1850, "median": 1550, "std_dev": 1050, "min_val": 0, "max_val": 9500, "p10": 320, "p25": 750, "p75": 2450, "p90": 3350},
        "electricity": {"mean": 2900, "median": 2600, "std_dev": 1250, "min_val": 0, "max_val": 9500, "p10": 950, "p25": 1650, "p75": 3650, "p90": 4700},
        "diet": {"mean": 1850, "median": 1750, "std_dev": 620, "min_val": 750, "max_val": 4900, "p10": 1000, "p25": 1400, "p75": 2250, "p90": 2800},
        "flights": {"mean": 1.3, "median": 1, "std_dev": 2.0, "min_val": 0, "max_val": 28, "p10": 0, "p25": 0, "p75": 2, "p90": 4},
        "footprint": {"mean": 5400, "median": 5000, "std_dev": 2350, "min_val": 1450, "max_val": 19000, "p10": 2150, "p25": 3400, "p75": 6700, "p90": 8800},
        "eco_score": {"mean": 63, "median": 63, "std_dev": 15, "min_val": 0, "max_val": 100, "p10": 39, "p25": 51, "p75": 75, "p90": 85}
    },
    "NL": {
        "name": "Netherlands", "region": "Europe",
        "transport": {"mean": 1600, "median": 1300, "std_dev": 1100, "min_val": 0, "max_val": 10000, "p10": 250, "p25": 650, "p75": 2200, "p90": 3100},
        "electricity": {"mean": 3200, "median": 2800, "std_dev": 1400, "min_val": 0, "max_val": 11000, "p10": 1100, "p25": 1900, "p75": 4000, "p90": 5200},
        "diet": {"mean": 1950, "median": 1850, "std_dev": 660, "min_val": 750, "max_val": 5100, "p10": 1050, "p25": 1450, "p75": 2350, "p90": 2950},
        "flights": {"mean": 2.2, "median": 1, "std_dev": 3.2, "min_val": 0, "max_val": 45, "p10": 0, "p25": 0, "p75": 3, "p90": 6},
        "footprint": {"mean": 6100, "median": 5500, "std_dev": 2600, "min_val": 1600, "max_val": 21000, "p10": 2500, "p25": 3800, "p75": 7800, "p90": 10000},
        "eco_score": {"mean": 59, "median": 59, "std_dev": 16, "min_val": 0, "max_val": 100, "p10": 34, "p25": 47, "p75": 71, "p90": 84}
    },
    "CH": {
        "name": "Switzerland", "region": "Europe",
        "transport": {"mean": 1500, "median": 1250, "std_dev": 1000, "min_val": 0, "max_val": 9000, "p10": 280, "p25": 650, "p75": 2100, "p90": 3000},
        "electricity": {"mean": 2200, "median": 1900, "std_dev": 1100, "min_val": 0, "max_val": 8000, "p10": 850, "p25": 1400, "p75": 2800, "p90": 3800},
        "diet": {"mean": 2050, "median": 1950, "std_dev": 680, "min_val": 800, "max_val": 5300, "p10": 1100, "p25": 1550, "p75": 2450, "p90": 3050},
        "flights": {"mean": 2.5, "median": 2, "std_dev": 3.5, "min_val": 0, "max_val": 50, "p10": 0, "p25": 0, "p75": 4, "p90": 7},
        "footprint": {"mean": 5500, "median": 5000, "std_dev": 2400, "min_val": 1500, "max_val": 19000, "p10": 2200, "p25": 3500, "p75": 7000, "p90": 9200},
        "eco_score": {"mean": 65, "median": 65, "std_dev": 15, "min_val": 0, "max_val": 100, "p10": 42, "p25": 54, "p75": 77, "p90": 87}
    },
    "NO": {
        "name": "Norway", "region": "Europe",
        "transport": {"mean": 1300, "median": 1100, "std_dev": 850, "min_val": 0, "max_val": 7500, "p10": 220, "p25": 550, "p75": 1800, "p90": 2600},
        "electricity": {"mean": 1500, "median": 1300, "std_dev": 800, "min_val": 0, "max_val": 6000, "p10": 600, "p25": 1000, "p75": 2000, "p90": 2800},
        "diet": {"mean": 1800, "median": 1700, "std_dev": 600, "min_val": 700, "max_val": 4800, "p10": 1000, "p25": 1350, "p75": 2150, "p90": 2650},
        "flights": {"mean": 2.0, "median": 1, "std_dev": 2.8, "min_val": 0, "max_val": 40, "p10": 0, "p25": 0, "p75": 3, "p90": 5},
        "footprint": {"mean": 4300, "median": 3900, "std_dev": 1900, "min_val": 1200, "max_val": 16000, "p10": 1900, "p25": 2900, "p75": 5600, "p90": 7200},
        "eco_score": {"mean": 72, "median": 72, "std_dev": 13, "min_val": 0, "max_val": 100, "p10": 50, "p25": 62, "p75": 84, "p90": 93}
    },
    "FI": {
        "name": "Finland", "region": "Europe",
        "transport": {"mean": 1500, "median": 1250, "std_dev": 950, "min_val": 0, "max_val": 8500, "p10": 260, "p25": 620, "p75": 2100, "p90": 2900},
        "electricity": {"mean": 2400, "median": 2100, "std_dev": 1150, "min_val": 0, "max_val": 8500, "p10": 950, "p25": 1500, "p75": 3100, "p90": 4200},
        "diet": {"mean": 1850, "median": 1750, "std_dev": 620, "min_val": 750, "max_val": 4900, "p10": 1000, "p25": 1400, "p75": 2200, "p90": 2750},
        "flights": {"mean": 1.6, "median": 1, "std_dev": 2.4, "min_val": 0, "max_val": 35, "p10": 0, "p25": 0, "p75": 2, "p90": 4},
        "footprint": {"mean": 4900, "median": 4500, "std_dev": 2100, "min_val": 1350, "max_val": 17000, "p10": 2100, "p25": 3200, "p75": 6200, "p90": 8000},
        "eco_score": {"mean": 68, "median": 68, "std_dev": 14, "min_val": 0, "max_val": 100, "p10": 45, "p25": 58, "p75": 80, "p90": 90}
    },
    "DK": {
        "name": "Denmark", "region": "Europe",
        "transport": {"mean": 1400, "median": 1150, "std_dev": 900, "min_val": 0, "max_val": 8000, "p10": 240, "p25": 580, "p75": 1950, "p90": 2700},
        "electricity": {"mean": 2100, "median": 1850, "std_dev": 1050, "min_val": 0, "max_val": 7500, "p10": 850, "p25": 1350, "p75": 2700, "p90": 3700},
        "diet": {"mean": 2000, "median": 1900, "std_dev": 670, "min_val": 800, "max_val": 5200, "p10": 1050, "p25": 1500, "p75": 2400, "p90": 3000},
        "flights": {"mean": 1.8, "median": 1, "std_dev": 2.6, "min_val": 0, "max_val": 38, "p10": 0, "p25": 0, "p75": 3, "p90": 5},
        "footprint": {"mean": 4600, "median": 4200, "std_dev": 2000, "min_val": 1250, "max_val": 16500, "p10": 1950, "p25": 3000, "p75": 5800, "p90": 7600},
        "eco_score": {"mean": 69, "median": 69, "std_dev": 14, "min_val": 0, "max_val": 100, "p10": 46, "p25": 59, "p75": 81, "p90": 91}
    },
    "AT": {
        "name": "Austria", "region": "Europe",
        "transport": {"mean": 1750, "median": 1450, "std_dev": 1050, "min_val": 0, "max_val": 9200, "p10": 310, "p25": 720, "p75": 2400, "p90": 3300},
        "electricity": {"mean": 2600, "median": 2300, "std_dev": 1150, "min_val": 0, "max_val": 8800, "p10": 950, "p25": 1550, "p75": 3300, "p90": 4400},
        "diet": {"mean": 1900, "median": 1800, "std_dev": 640, "min_val": 750, "max_val": 5000, "p10": 1000, "p25": 1400, "p75": 2300, "p90": 2850},
        "flights": {"mean": 1.5, "median": 1, "std_dev": 2.2, "min_val": 0, "max_val": 32, "p10": 0, "p25": 0, "p75": 2, "p90": 4},
        "footprint": {"mean": 5100, "median": 4700, "std_dev": 2200, "min_val": 1400, "max_val": 17500, "p10": 2100, "p25": 3200, "p75": 6400, "p90": 8300},
        "eco_score": {"mean": 65, "median": 65, "std_dev": 15, "min_val": 0, "max_val": 100, "p10": 41, "p25": 53, "p75": 78, "p90": 88}
    },
    "BE": {
        "name": "Belgium", "region": "Europe",
        "transport": {"mean": 1900, "median": 1600, "std_dev": 1150, "min_val": 0, "max_val": 10500, "p10": 350, "p25": 850, "p75": 2600, "p90": 3600},
        "electricity": {"mean": 3100, "median": 2700, "std_dev": 1350, "min_val": 0, "max_val": 10500, "p10": 1050, "p25": 1850, "p75": 3900, "p90": 5100},
        "diet": {"mean": 2000, "median": 1900, "std_dev": 680, "min_val": 800, "max_val": 5200, "p10": 1100, "p25": 1500, "p75": 2400, "p90": 3000},
        "flights": {"mean": 1.7, "median": 1, "std_dev": 2.5, "min_val": 0, "max_val": 36, "p10": 0, "p25": 0, "p75": 3, "p90": 5},
        "footprint": {"mean": 5700, "median": 5200, "std_dev": 2500, "min_val": 1500, "max_val": 19500, "p10": 2300, "p25": 3600, "p75": 7200, "p90": 9300},
        "eco_score": {"mean": 61, "median": 61, "std_dev": 15, "min_val": 0, "max_val": 100, "p10": 37, "p25": 49, "p75": 73, "p90": 83}
    },
    "IE": {
        "name": "Ireland", "region": "Europe",
        "transport": {"mean": 2000, "median": 1700, "std_dev": 1200, "min_val": 0, "max_val": 11000, "p10": 380, "p25": 900, "p75": 2750, "p90": 3800},
        "electricity": {"mean": 3300, "median": 2900, "std_dev": 1450, "min_val": 0, "max_val": 11500, "p10": 1150, "p25": 1950, "p75": 4150, "p90": 5400},
        "diet": {"mean": 2100, "median": 2000, "std_dev": 700, "min_val": 850, "max_val": 5500, "p10": 1150, "p25": 1550, "p75": 2500, "p90": 3150},
        "flights": {"mean": 2.6, "median": 2, "std_dev": 3.6, "min_val": 0, "max_val": 55, "p10": 0, "p25": 0, "p75": 4, "p90": 8},
        "footprint": {"mean": 6300, "median": 5800, "std_dev": 2700, "min_val": 1700, "max_val": 22000, "p10": 2600, "p25": 4000, "p75": 8100, "p90": 10500},
        "eco_score": {"mean": 57, "median": 57, "std_dev": 16, "min_val": 0, "max_val": 100, "p10": 33, "p25": 45, "p75": 69, "p90": 81}
    },
"""

# Insert right before the last closing brace in datasets.py
content = content.replace("    }\n}", countries_data + "    }\n}")

with open(datasets_file, "w") as f:
    f.write(content)
