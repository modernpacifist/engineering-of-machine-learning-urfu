#!/bin/env python3

from pyspark.sql import SparkSession

def main():
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("WordCount") \
        .master("local[*]") \
        .getOrCreate()
    
    # Create Spark context
    sc = spark.sparkContext
    
    # Path to your input text file
    # Replace with your actual input file path
    input_path = "input.txt"
    
    # Read the text file
    text_file = sc.textFile(input_path)
    
    # Split each line into words and flatten the result
    words = text_file.flatMap(lambda line: line.split(" "))
    
    # Map each word to a key-value pair (word, 1) and reduce by key
    word_counts = words.map(lambda word: (word, 1)) \
                       .reduceByKey(lambda a, b: a + b)
    
    # Sort results by word count (optional)
    word_counts_sorted = word_counts.sortBy(lambda x: x[1], ascending=False)
    
    # Collect results and print
    results = word_counts_sorted.collect()
    for word, count in results:
        if word:  # Skip empty words
            print(f"{word}: {count}")
    
    # Save results to a file (optional)
    # word_counts_sorted.saveAsTextFile("word_count_output")
    
    # Stop the Spark session
    spark.stop()

if __name__ == "__main__":
    main()
