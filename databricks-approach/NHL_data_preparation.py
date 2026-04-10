# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC ### # Step 1. Converting json to a dataframe

# COMMAND ----------

from pyspark.sql.functions import explode, col, when

path = "/Volumes/katalogi/default/nhl_datat/standings_20242025_snapshot.json"
raw_standings_df = spark.read.option("multiline", True).json(path)



# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 2. Flatten the standigs array and extract the columns and correct Toronto points
# MAGIC - The JSON has a top-level key called 'standings'. We turn each item in that list into a row.
# MAGIC - We reach into the nested objects (teamName.default) to get the strings
# MAGIC - Lastly we correct Toronto points (+2)

# COMMAND ----------

flattened_standings_df = raw_standings_df.select(explode("standings").alias("team"))

silver_standings = flattened_standings_df.select(
  col("team.teamName.default").alias("team_name"),
    col("team.teamAbbrev.default").alias("team_abbrev"), # Kept temporarily for logic
    col("team.wins").cast("int").alias("wins"),
    col("team.points").cast("int").alias("points_api")
).withColumn(
    "total_points",
    # We use team_abbrev here to perform the correction
    when(col("team_abbrev") == "TOR", col("points_api") + 2).otherwise(col("points_api"))
).select(
    # Now we only select the final columns we want the user to see
    "team_name", 
    "wins", 
    "total_points"
)

# Display to verify it's now just 3 clean columns
display(silver_standings.orderBy(col("total_points").desc()))
  

 


                                                 
                                                 
                                                

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 3. Save the table

# COMMAND ----------

silver_standings.write.mode("overwrite").saveAsTable("katalogi.default.nhl_silver_standings")
