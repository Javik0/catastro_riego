try:
    import shapely
    from shapely.geometry import shape
    print("✓ shapely disponible")
except ImportError:
    print("❌ shapely no disponible")
