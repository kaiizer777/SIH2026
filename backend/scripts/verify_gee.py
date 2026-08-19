import ee

PROJECT_ID = "sih25071-rockfall"

try:
    ee.Initialize(project=PROJECT_ID)
    result = ee.String('GEE session verified').getInfo()
    print(f"SUCCESS: {result}")
except Exception as e:
    print(f"FAILED: {e}")
