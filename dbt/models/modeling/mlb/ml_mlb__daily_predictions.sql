{{-
	config(
		materialized='view',
		tags=["modeling", "mlb"]
	)
-}}

select *
from {{ ref('ml_mlb__final_features') }}
where game_date = (select max(game_date) from {{ ref('ml_mlb__final_features') }})

