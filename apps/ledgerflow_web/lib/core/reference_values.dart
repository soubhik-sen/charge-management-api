const chargeCategoryValues = <String>[
  'ACCESSORIAL',
  'ADJUSTMENT',
  'COMPLIANCE',
  'CUSTOMS',
  'DESTINATION',
  'DOCUMENTATION',
  'EQUIPMENT',
  'FREIGHT',
  'HANDLING',
  'INSURANCE',
  'MARGIN',
  'ORIGIN',
  'RISK',
  'SECURITY',
  'SURCHARGE',
  'TAX',
  'TIME_BASED',
];

const chargeContextValues = <String>[
  'AIR',
  'COMMERCIAL',
  'COMMODITY',
  'COMPLIANCE',
  'CUSTOMS',
  'DESTINATION',
  'EQUIPMENT',
  'FINANCE',
  'ORIGIN',
  'PORT',
  'SECURITY',
  'TAX',
  'TRANSPORT',
  'ROAD',
  'WAREHOUSE',
];

const chargeCalculationBasisValues = <String>[
  'FLAT',
  'SHIPMENT',
  'DOCUMENT',
  'HEADER',
  'PERCENTAGE',
  'WEIGHT',
  'CHARGEABLE_WEIGHT',
  'VOLUME',
  'CONTAINER',
  'PER_CONTAINER',
  'PACKAGE',
  'QUANTITY',
  'DAY',
  'PER_DAY',
  'DISTANCE',
  'PER_HOUR',
  'PER_LOADING_METER',
  'PER_PALLET',
  'PER_STOP',
];

const currencyValues = <String>['EUR', 'GBP', 'USD'];

const transportModeValues = <String>['AIR', 'OCEAN', 'RAIL', 'ROAD'];

const equipmentTypeValues = <String>[
  'ANY',
  'BOX_TRUCK',
  'CURTAINSIDER',
  'DRY_VAN',
  'FLATBED',
  'REEFER',
  'ROAD_TANKER',
  'SWAP_BODY',
  '20GP',
  '40GP',
  '40HC',
];

const serviceLevelValues = <String>[
  'ECONOMY',
  'EXPRESS',
  'NEXT_DAY',
  'SAME_DAY',
  'STANDARD',
  'TIME_DEFINITE',
];

List<String> referenceValuesWithCurrent(List<String> values, String current) {
  final normalized = current.trim().toUpperCase();
  if (normalized.isEmpty || values.contains(normalized)) return values;
  return [...values, normalized]..sort();
}
