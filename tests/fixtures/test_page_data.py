"""
Test fixtures for page classification and table processing.

Contains synthetic and real-world examples of different page types
and table structures for testing parser hardening.
"""
import pandas as pd
from typing import Dict, List, Any


# Sample page texts for different classifications
TITLE_PAGE_TEXT = """
HAGER DOOR HARDWARE
PRICE BOOK #17

Effective 3/31/2025

One Family. One Brand. One Vision.

webmaster@hagerco.com
orders@hagerco.com
139 Victor Street
Saint Louis, MO 63104
800-325-9995 (main phone)
314-772-4400 (local phone)
www.hagerco.com
"""

TABLE_OF_CONTENTS_TEXT = """
TABLE OF CONTENTS

ARCHITECTURAL FINISH SYMBOLS............................ 9
PRICING RULES........................................... 11
HINGE ADDITIONS........................................ 13
BALL BEARING HINGES.................................... 15
    BB1100 Series...................................... 16
    BB1279 Series...................................... 18
TEMPLATE HINGES........................................ 25
    TH1100 Series...................................... 26
SPRING HINGES.......................................... 35
"""

FINISH_SYMBOLS_TEXT = """
ARCHITECTURAL FINISH SYMBOLS

BHMA Symbol    Description                    Price
US3            Bright Brass                   $12.50
US4            Satin Brass                    $15.75
US10           Satin Bronze                   $18.25
US10A          Satin Bronze                   $18.25
US10B          Dark Bronze                    $18.25
US15           Satin Nickel                   $20.50
US26           Bright Chrome                  $22.75
US26D          Satin Chrome                   $22.75
2C             Plain Zinc Plate               20% above US10A or US10B price
3              Bright Brass                   Use price of US10B
3A             Antique Brass                  25% above US10A price
"""

PRICE_RULES_TEXT = """
PRICING RULES

General Rules:
- US10B use US10A price
- For US33D use US32D price
- US5 uses US4 pricing
- 2C finish: 20% above US10A or US10B price
- 3A finish: 25% above US10A price

Special Considerations:
- Net prices shown are for standard duty hinges
- Heavy duty hinges add 15% to net price
- Custom finishes quoted on request
"""

OPTION_LIST_TEXT = """
HINGE ADDITIONS

PREPARATION OPTIONS:
EPT    Electroplated Preparation         add $25.00
CTW    Continuous Transfer Wire          add $35.50
ETW    Electric Thru-Wire               add $45.75
EMS    Electromagnetic Shielding        add $55.25

MATERIAL OPTIONS:
HWS    Heavy Weight Stainless           add $85.00
FR3    Fire Rated 3 Hour               add $125.00
TIPIT  Template in Place Installation   add $15.50
"""

DATA_TABLE_TEXT = """
BB1100 SERIES - BALL BEARING HEAVY DUTY

Model      Size       Description              US3      US4      US10B    US26D
BB1100-1   4.5" x 4"  Standard Weight         $125.50  $128.75  $135.25  $142.00
BB1100-2   5" x 4.5"  Standard Weight         $135.75  $139.25  $146.50  $153.75
BB1100-3   6" x 4.5"  Heavy Duty              $156.25  $160.50  $168.75  $177.25

Special Features:
- Ball bearing construction
- Removable pin
- Non-rising pin design
"""

# Sample table data for different structures
SIMPLE_TABLE_DATA = [
    ['Model', 'Description', 'Price'],
    ['BB1100US3', 'Ball Bearing Heavy', '$125.50'],
    ['BB1100US4', 'Ball Bearing Heavy', '$128.75'],
    ['BB1100US10B', 'Ball Bearing Heavy', '$135.25']
]

MULTI_ROW_HEADER_TABLE = [
    ['', '', 'Finish Options', 'Finish Options', 'Finish Options'],
    ['Model', 'Description', 'US3', 'US4', 'US10B'],
    ['BB1100-1', 'Standard Weight', '$125.50', '$128.75', '$135.25'],
    ['BB1100-2', 'Standard Weight', '$135.75', '$139.25', '$146.50']
]

MERGED_CELLS_TABLE = [
    ['BB1100 Series', '', '', ''],
    ['Model', 'Size', 'Description', 'Price'],
    ['BB1100-1', '4.5" x 4"', 'Standard Weight', '$125.50'],
    ['BB1100-2', '5" x 4.5"', 'Standard Weight', '$135.75'],
    ['', '', 'Special Notes:', ''],
    ['', '', 'Ball bearing construction', ''],
    ['', '', 'Removable pin design', '']
]

CROSS_PAGE_TABLE_1 = [
    ['Model', 'Description', 'US3 Price'],
    ['BB1100-1', 'Standard Weight', '$125.50'],
    ['BB1100-2', 'Standard Weight', '$135.75'],
    ['BB1100-3', 'Heavy Duty', '$156.25']
]

CROSS_PAGE_TABLE_2 = [
    ['Model', 'Description', 'US3 Price'],
    ['BB1100-4', 'Heavy Duty', '$167.50'],
    ['BB1100-5', 'Super Heavy', '$189.75'],
    ['BB1100-6', 'Super Heavy', '$212.25']
]

ROTATED_TABLE_SIMULATION = [
    ['M', 'B', '$'],
    ['o', 'B', '1'],
    ['d', '1', '2'],
    ['e', '1', '5'],
    ['l', '0', '.'],
    ['', '0', '5'],
    ['', '', '0']
]

CURRENCY_VARIATIONS_TABLE = [
    ['Model', 'Price USD', 'Price CAD'],
    ['BB1100-1', '$ 125.50', 'CAD 165.25'],
    ['BB1100-2', '$135 .75', 'CAD175.50'],
    ['BB1100-3', '156.25 USD', 'CAD 205.75']
]


def get_test_page_data() -> Dict[str, Dict[str, Any]]:
    """Get test page data for different page types."""
    return {
        'title_page': {
            'text': TITLE_PAGE_TEXT,
            'page_number': 1,
            'tables': [],
            'expected_type': 'title_page'
        },
        'toc_page': {
            'text': TABLE_OF_CONTENTS_TEXT,
            'page_number': 2,
            'tables': [],
            'expected_type': 'table_of_contents'
        },
        'finish_symbols': {
            'text': FINISH_SYMBOLS_TEXT,
            'page_number': 9,
            'tables': [pd.DataFrame(SIMPLE_TABLE_DATA[1:], columns=SIMPLE_TABLE_DATA[0])],
            'expected_type': 'finish_symbols'
        },
        'price_rules': {
            'text': PRICE_RULES_TEXT,
            'page_number': 11,
            'tables': [],
            'expected_type': 'price_rules'
        },
        'option_list': {
            'text': OPTION_LIST_TEXT,
            'page_number': 13,
            'tables': [],
            'expected_type': 'option_list'
        },
        'data_table': {
            'text': DATA_TABLE_TEXT,
            'page_number': 16,
            'tables': [pd.DataFrame(SIMPLE_TABLE_DATA[1:], columns=SIMPLE_TABLE_DATA[0])],
            'expected_type': 'data_table'
        }
    }


def get_test_table_structures() -> Dict[str, Dict[str, Any]]:
    """Get test table structures for processing tests."""
    return {
        'simple_table': {
            'data': SIMPLE_TABLE_DATA,
            'expected_rows': 3,
            'expected_cols': 3,
            'has_header': True,
            'has_merged_cells': False
        },
        'multi_row_header': {
            'data': MULTI_ROW_HEADER_TABLE,
            'expected_rows': 2,  # After header welding
            'expected_cols': 3,
            'has_header': True,
            'has_merged_cells': False,
            'header_rows': 2
        },
        'merged_cells': {
            'data': MERGED_CELLS_TABLE,
            'expected_rows': 4,  # After processing
            'expected_cols': 4,
            'has_header': True,
            'has_merged_cells': True
        },
        'rotated_simulation': {
            'data': ROTATED_TABLE_SIMULATION,
            'expected_rows': 1,  # Most data will be filtered out
            'expected_cols': 3,
            'has_header': False,
            'needs_rotation_fix': True
        },
        'currency_variations': {
            'data': CURRENCY_VARIATIONS_TABLE,
            'expected_rows': 3,
            'expected_cols': 3,
            'has_header': True,
            'needs_currency_normalization': True
        }
    }


def get_cross_page_test_data() -> List[Dict[str, Any]]:
    """Get test data for cross-page table stitching."""
    return [
        {
            'page_number': 16,
            'table_data': CROSS_PAGE_TABLE_1,
            'fingerprint': 'model|description|us3_price#3x3#TTN'
        },
        {
            'page_number': 17,
            'table_data': CROSS_PAGE_TABLE_2,
            'fingerprint': 'model|description|us3_price#3x3#TTN'
        }
    ]


def get_ocr_test_scenarios() -> Dict[str, Dict[str, Any]]:
    """Get test scenarios for OCR processing."""
    return {
        'low_text_extraction': {
            'text': 'BB',  # Very short text
            'tables': [],
            'should_trigger_ocr': True,
            'reason': 'insufficient_text'
        },
        'missing_expected_tables': {
            'text': 'Model Description Price Series BB1100 Ball Bearing $125.50',
            'tables': [],
            'should_trigger_ocr': True,
            'reason': 'table_indicators_no_tables'
        },
        'low_confidence_tables': {
            'text': 'Standard table text with good extraction',
            'tables': [{'confidence': 0.2}],  # Low confidence table
            'should_trigger_ocr': True,
            'reason': 'low_table_confidence'
        },
        'good_extraction': {
            'text': 'Model BB1100-1 Description Ball Bearing Heavy Price $125.50',
            'tables': [{'confidence': 0.9}],
            'should_trigger_ocr': False,
            'reason': 'good_quality'
        }
    }


def get_confidence_test_cases() -> List[Dict[str, Any]]:
    """Get test cases for confidence scoring."""
    return [
        {
            'name': 'high_quality_table',
            'data': SIMPLE_TABLE_DATA,
            'expected_confidence_range': (0.8, 1.0),
            'features': {
                'complete_data': True,
                'consistent_types': True,
                'good_headers': True
            }
        },
        {
            'name': 'sparse_table',
            'data': [
                ['Model', 'Price', ''],
                ['BB1100', '', ''],
                ['', '$125.50', ''],
                ['', '', '']
            ],
            'expected_confidence_range': (0.3, 0.6),
            'features': {
                'complete_data': False,
                'consistent_types': False,
                'good_headers': True
            }
        },
        {
            'name': 'processed_with_corrections',
            'data': MULTI_ROW_HEADER_TABLE,
            'expected_confidence_range': (0.7, 0.9),
            'features': {
                'header_welded': True,
                'structure_improved': True
            }
        }
    ]


# Property-based test generators
def generate_price_variations() -> List[str]:
    """Generate different price format variations for testing normalization."""
    base_prices = ['125.50', '1250.75', '25.00']
    formats = [
        lambda p: f'${p}',           # $125.50
        lambda p: f'$ {p}',          # $ 125.50
        lambda p: f'${p[:-3]} .{p[-2:]}',  # $125 .50
        lambda p: f'{p} USD',        # 125.50 USD
        lambda p: f'USD {p}',        # USD 125.50
        lambda p: f'{p.replace(".", ",")}',  # European format
    ]

    variations = []
    for price in base_prices:
        for fmt in formats:
            try:
                variations.append(fmt(price))
            except:
                pass  # Skip invalid combinations

    return variations


def generate_model_code_variations() -> List[str]:
    """Generate different model code format variations."""
    return [
        'BB1100',
        'BB 1100',
        'BB-1100',
        'BB1100US3',
        'BB1100-US3',
        'BB1100 US3',
        'bb1100',  # Lowercase
        'BB1100-1',
        'BB1100/1'
    ]


def generate_finish_code_variations() -> List[str]:
    """Generate different finish code format variations."""
    return [
        'US3',
        'US 3',
        'US-3',
        'us3',     # Lowercase
        'US10B',
        'US10 B',
        'US10-B',
        '2C',
        '3A',
        'BHMA US3'
    ]