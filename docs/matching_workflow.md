# Matching Workflow: Unidentified to Missing Persons

## Data Available

### Open Data Sources (Loaded)
| Source | Records | Type |
|--------|---------|------|
| BC Coroners UHR | 153 cases | Unidentified remains |
| BC Cities | 18 cities | Geographic reference |
| First Nations Reserves | 200 locations | Geographic reference |

### Restricted Data Sources (Require Permission)
| Source | Access Method |
|--------|--------------|
| NCMPUR (Canada's Missing) | Requires RCMP data agreement |
| NamUs (US) | API requires registration |
| Individual police records | FOIA/ATI request |

---

## Priority Cases to Match (Recent 2020-2024)

### 2023-3008-0034
- **Profile**: Male, 20-35yo, Caucasian, Brown hair
- **Location**: Downtown Vancouver (49.28°N, -123.12°W)
- **Unique Items**: G-Shock watch, Timex watch, gold signet ring
- **Search Terms**: male missing Vancouver 2018-2023, gold signet ring

### 2023-3008-0169
- **Profile**: Male, 25-40yo, Black, Black hair, Brown eyes
- **Location**: Vancouver (49.28°N, -123.10°W)
- **Unique Items**: Blundstone boots, 10cm keloid scar on back
- **Search Terms**: male missing Vancouver Black 2018-2023

### 2022-0290-0103
- **Profile**: Male, 20-40yo, Asian, Black hair, Brown eyes
- **Location**: Richmond (49.20°N, -123.02°W)
- **Unique Items**: Red Taiga coat, Adidas runners size 10.5
- **Search Terms**: Asian male missing BC 2017-2022, Taiga jacket

### 2022-5054-0163
- **Profile**: Male, 20-30yo, Black hair, curly beard
- **Location**: North Vancouver (49.35°N, -123.11°W)
- **Unique Items**: Uniqlo sweater, Monte Carlo thermal
- **Weight**: 87.3kg
- **Search Terms**: male missing North Vancouver 2017-2022

---

## Legal Search Methods

1. **Public Police Press Releases**
   - VPD missing persons bulletins
   - RCMP BC news releases
   - Crime Stoppers BC

2. **News Archives**
   - Search local news for missing persons reports matching timeframe

3. **Formal Data Requests**
   - BC Coroners Service (public inquiries)
   - RCMP ATIP request for aggregate data

---

## Matching Algorithm

For each unidentified case, match against missing persons using:

```
Score = Σ weights × matches

Weights:
- Sex match: 0.20
- Age overlap: 0.15  
- Race match: 0.15
- Geographic proximity: 0.15
- Timeframe overlap: 0.15
- Physical descriptors: 0.10
- Clothing/items: 0.10
```

Matches with score > 0.70 should be flagged for human review.
