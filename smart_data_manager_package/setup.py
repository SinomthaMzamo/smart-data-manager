# smart_data_manager_package/setup.py

from setuptools import setup, find_packages

setup(
    name='smart-data-manager',  # Must be unique on PyPI! Choose a descriptive, unique name.
    version='1.0.19',            # Start with a version number
    # 💡 FIX 1: Map the source directory name (with underscores)
    package_dir={'smart_data_manager': '.'},
    
    # 💡 FIX 2: Explicitly tell Python the importable package name
    packages=['smart_data_manager'],
    # Declare the required third-party libraries this package needs at runtime
    install_requires=[
        'pandas>=2.2',
        'SQLAlchemy>=2.0',
        'pyodbc>=5.1',
        # Do NOT list azure-functions or python-dotenv here, only dependencies of your core logic
    ],
    # --- ADD THIS SECTION ---
    package_data={
        'smart_data_manager': ['*.sql'],
    },
    include_package_data=True,
    # Add optional metadata
    author='Sinomtha Mzamo',
    description='ETL logic for Smart Data Manager.',
    long_description=open('README.md').read(), # Use README if available
    long_description_content_type='text/markdown',
)