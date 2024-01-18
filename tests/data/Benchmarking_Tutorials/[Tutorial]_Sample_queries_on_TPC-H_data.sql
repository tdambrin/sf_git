/* Tutorial 1: Sample queries on TPC-H data

Prerequisites
This tutorial requires the Snowflake provided
snowflake_sample_data database.  If you don't
have this database already in your account 
please add it by following these instructions:
https://docs.snowflake.net/manuals/user-guide/sample-data-using.html
 
Pricing Summary Report Query (Q1) 
This query demonstrates basic SQL 
functionality using the included TPC-H sample
data.  The results are the amount of business
that was billed, shipped, and returned. 

Business Question: The Pricing Summary Report
Query provides a summary pricing report for 
all line items shipped as of a given date. The
date is within 60 - 120 days of the greatest 
ship date contained in the database. The query
lists totals for extended price, discounted 
extended price, discounted extended price plus
tax, average quantity, average extended price,
and average discount. These aggregates are 
grouped by RETURNFLAG and LINESTATUS, and 
listed in ascending order of RETURNFLAG and 
LINESTATUS. A count of the number of line items
in each group is included. 
*/

use schema snowflake_sample_data.tpch_sf1; 
-- or tpch_sf100, tpch_sf1000

SELECT
l_returnflag,
l_linestatus,
sum(l_quantity) as sum_qty,
sum(l_extendedprice) as sum_base_price,
sum(l_extendedprice * (1-l_discount)) 
  as sum_disc_price,
sum(l_extendedprice * (1-l_discount) * 
  (1+l_tax)) as sum_charge,
avg(l_quantity) as avg_qty,
avg(l_extendedprice) as avg_price,
avg(l_discount) as avg_disc,
count(*) as count_order
FROM
lineitem
WHERE
l_shipdate <= dateadd(day, -90, to_date('1998-12-01'))
GROUP BY
l_returnflag,
l_linestatus
ORDER BY
l_returnflag,
l_linestatus;

