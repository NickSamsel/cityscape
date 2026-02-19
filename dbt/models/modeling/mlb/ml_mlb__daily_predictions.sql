{{-
	config(
		materialized='view',
		tags=["modeling", "mlb"]
	)
-}}

select *
from {{ ref('ml_mlb__prediction_dataset') }}

