# TheLook batch profile: 20261005T161059Z

Profiled at UTC: 2026-10-06T09:25:05.199564+00:00

Scope: all seven tables in one extract batch, compared with Snowflake RAW. All checks filter by this batch ID; earlier batches are excluded.

## Row counts and candidate primary keys

| Table | Parquet rows | RAW rows | Key | Distinct keys | Null keys | Duplicate key rows |
|---|---:|---:|---|---:|---:|---:|
| distribution_centers | 10 | 10 | ID | 10 | 0 | 0 |
| events | 2,426,288 | 2,426,288 | ID | 2,426,288 | 0 | 0 |
| inventory_items | 490,655 | 490,655 | ID | 490,655 | 0 | 0 |
| order_items | 181,758 | 181,758 | ID | 181,758 | 0 | 0 |
| orders | 125,564 | 125,564 | ORDER_ID | 125,564 | 0 | 0 |
| products | 29,120 | 29,120 | ID | 29,120 | 0 | 0 |
| users | 100,000 | 100,000 | ID | 100,000 | 0 | 0 |

## Nullable fields and temporal coverage (UTC)

### distribution_centers

Observed null counts: none.


### events

Observed null counts: USER_ID: 1,124,536.

- CREATED_AT: 2019-01-02 00:20:00+00:00 through 2026-10-09 00:12:42.955962+00:00
- CREATED_AT after extraction time: 1,464 rows

Event type counts: product: 843,964; cart: 593,782; department: 593,640; purchase: 181,758; cancel: 125,042; home: 88,102.

### inventory_items

Observed null counts: SOLD_AT: 308,897.

- CREATED_AT: 2018-11-19 19:23:15+00:00 through 2026-10-08 16:02:49.066005+00:00
- SOLD_AT: 2019-01-06 06:43:15+00:00 through 2026-10-09 00:12:42.955962+00:00
- CREATED_AT after extraction time: 37 rows
- SOLD_AT after extraction time: 1,464 rows

### order_items

Observed null counts: SHIPPED_AT: 63,519; DELIVERED_AT: 118,460; RETURNED_AT: 163,370.

- CREATED_AT: 2019-01-06 06:43:15+00:00 through 2026-10-09 00:12:42.955962+00:00
- SHIPPED_AT: 2019-01-15 03:25:59+00:00 through 2026-10-07 23:18:25.156841+00:00
- DELIVERED_AT: 2019-01-26 18:43:55+00:00 through 2026-10-12 14:02:24.280832+00:00
- RETURNED_AT: 2019-02-11 15:12:22+00:00 through 2026-10-14 00:45:25.156841+00:00
- CREATED_AT after extraction time: 1,464 rows
- SHIPPED_AT after extraction time: 1,400 rows
- DELIVERED_AT after extraction time: 1,861 rows
- RETURNED_AT after extraction time: 672 rows

Status counts: Shipped: 54,941; Complete: 44,910; Processing: 36,040; Cancelled: 27,479; Returned: 18,388.

### orders

Observed null counts: RETURNED_AT: 112,860; SHIPPED_AT: 43,846; DELIVERED_AT: 81,717.

- CREATED_AT: 2019-01-06 07:16:43+00:00 through 2026-10-05 00:47:46.196982+00:00
- RETURNED_AT: 2019-02-11 15:12:22+00:00 through 2026-10-14 00:45:25.156841+00:00
- SHIPPED_AT: 2019-01-15 03:25:59+00:00 through 2026-10-07 23:18:25.156841+00:00
- DELIVERED_AT: 2019-01-26 18:43:55+00:00 through 2026-10-12 14:02:24.280832+00:00
- RETURNED_AT after extraction time: 472 rows
- SHIPPED_AT after extraction time: 967 rows
- DELIVERED_AT after extraction time: 1,305 rows

Status counts: Shipped: 37,871; Complete: 31,143; Processing: 24,920; Cancelled: 18,926; Returned: 12,704.

### products

Observed null counts: NAME: 2; BRAND: 24.


### users

Observed null counts: none.

- CREATED_AT: 2019-01-02 00:23:00+00:00 through 2026-10-04 19:36:46.420500+00:00

## Relationships

| Child key | Parent key | Non-null orphan rows |
|---|---|---:|
| orders.USER_ID | users.ID | 0 |
| order_items.ORDER_ID | orders.ORDER_ID | 0 |
| order_items.USER_ID | users.ID | 0 |
| order_items.PRODUCT_ID | products.ID | 0 |
| order_items.INVENTORY_ITEM_ID | inventory_items.ID | 0 |
| inventory_items.PRODUCT_ID | products.ID | 0 |
| inventory_items.PRODUCT_DISTRIBUTION_CENTER_ID | distribution_centers.ID | 0 |
| products.DISTRIBUTION_CENTER_ID | distribution_centers.ID | 0 |
| events.USER_ID | users.ID | 0 |

Null foreign keys are reported separately above and are not counted as orphans.

## Business consistency

- order_item_user_mismatches: 0
- order_item_count_mismatches: 0

## Modeling implications and limits

- RAW is append-only. Candidate keys apply within a batch; use (_BATCH_ID, source key) for RAW tests. Staging must explicitly select a complete batch before enforcing source-key uniqueness.
- Tables were read sequentially. A shared batch ID does not provide a transactionally consistent source snapshot. Count equality cannot detect every concurrent source change.
- Source timestamps can be later than extraction time. Preserve them, flag them for business interpretation, and avoid assuming that all source timestamps are bounded by the ingestion date.
- One full snapshot does not establish source update/delete behavior or provide historical dimension changes. Incremental loading and SCD2 need evidence from subsequent extracts.
- Nullable lifecycle timestamps and anonymous event users must be assessed before adding not_null tests.
- This profile checks counts, candidate keys, nulls, temporal ranges and listed relationships; it does not prove full row-by-row equality or validate all business rules.
- No dbt business models or data tests were executed in this profiling step.
