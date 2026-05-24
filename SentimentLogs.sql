USE master;
GO

IF EXISTS (SELECT name FROM sys.databases WHERE name = N'SentimentAnalysisDB')
BEGIN
    ALTER DATABASE SentimentAnalysisDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE SentimentAnalysisDB;
END
GO

CREATE DATABASE SentimentAnalysisDB;
GO

USE SentimentAnalysisDB;
GO

CREATE TABLE SentimentLogs (
    ReviewID INT IDENTITY(1,1) PRIMARY KEY,
    ReviewDate DATETIME NOT NULL,
    StarRating INT NOT NULL,
    RawText NVARCHAR(MAX) NOT NULL,
    TranslatedText NVARCHAR(MAX) NULL,
    SentimentScore FLOAT NOT NULL, 
    Category VARCHAR(50) NOT NULL, 
    IsAnomaly BIT DEFAULT 0,
    DataSource VARCHAR(50) NOT NULL,
    ExtractionTimestamp DATETIME DEFAULT GETDATE()
);
GO

-- Retrieve all sentiment log records sorted by extraction timestamp in descending order
SELECT * FROM SentimentLogs 
ORDER BY ExtractionTimestamp DESC;

-- Retrieve the top 5 most recent reviews based on the user's review date
SELECT TOP 5 * FROM SentimentLogs 
ORDER BY ReviewDate DESC;

-- Retrieve all reviews flagged as anomalies due to sentiment-rating incongruence
SELECT * FROM SentimentLogs 
WHERE IsAnomaly = 1;

-- Retrieve all reviews processed using the synthetic fallback data source
SELECT * FROM SentimentLogs 
WHERE DataSource = 'SYNTHETIC_FALLBACK';

-- Retrieve all reviews strictly categorized as Negative
SELECT * FROM SentimentLogs 
WHERE Category = 'Negative';

-- Retrieve all 5-star reviews to analyze top-tier user feedback
SELECT * FROM SentimentLogs 
WHERE StarRating = 5;

-- Retrieve all 1-star reviews that were classified as Positive to investigate sarcasm
SELECT * FROM SentimentLogs 
WHERE StarRating = 1 AND Category = 'Positive';

-- Retrieve reviews where the raw text mentions specific keywords like 'error' or 'bug'
SELECT * FROM SentimentLogs 
WHERE RawText LIKE '%error%' OR RawText LIKE '%bug%';

-- Retrieve reviews extracted within the last 24 hours
SELECT * FROM SentimentLogs 
WHERE ExtractionTimestamp >= DATEADD(day, -1, GETDATE());

-- Retrieve reviews with a neutral sentiment score exactly equal to zero
SELECT * FROM SentimentLogs 
WHERE SentimentScore = 0.0;

-- Retrieve the total count of reviews grouped by their sentiment category
SELECT Category, COUNT(*) AS TotalReviews 
FROM SentimentLogs 
GROUP BY Category;

-- Retrieve the average sentiment score grouped by each star rating
SELECT StarRating, AVG(SentimentScore) AS AverageSentiment 
FROM SentimentLogs 
GROUP BY StarRating 
ORDER BY StarRating DESC;

-- Retrieve the count of anomalous versus standard reviews
SELECT IsAnomaly, COUNT(*) AS AnomalyCount 
FROM SentimentLogs 
GROUP BY IsAnomaly;

-- Retrieve the total volume of reviews partitioned by data source
SELECT DataSource, COUNT(*) AS ExtractionVolume 
FROM SentimentLogs 
GROUP BY DataSource;

-- Retrieve the minimum, maximum, and average sentiment scores across the entire dataset
SELECT 
    MIN(SentimentScore) AS MinScore, 
    MAX(SentimentScore) AS MaxScore, 
    AVG(SentimentScore) AS AvgScore 
FROM SentimentLogs;

-- Retrieve the daily volume of user reviews ordered chronologically
SELECT CAST(ReviewDate AS DATE) AS ReviewDay, COUNT(*) AS DailyVolume 
FROM SentimentLogs 
GROUP BY CAST(ReviewDate AS DATE) 
ORDER BY ReviewDay DESC;

-- Retrieve categories that have generated more than 10 reviews
SELECT Category, COUNT(*) AS Volume 
FROM SentimentLogs 
GROUP BY Category 
HAVING COUNT(*) > 10;

-- Retrieve star ratings where the average sentiment score is unexpectedly negative
SELECT StarRating, AVG(SentimentScore) AS AvgScore 
FROM SentimentLogs 
GROUP BY StarRating 
HAVING AVG(SentimentScore) < 0;

-- Retrieve the earliest and latest review dates stored in the vault
SELECT 
    MIN(ReviewDate) AS FirstReviewDate, 
    MAX(ReviewDate) AS LastReviewDate 
FROM SentimentLogs;

-- Retrieve the length of the raw text and sort by the longest reviews first
SELECT ReviewID, RawText, LEN(RawText) AS CharacterCount 
FROM SentimentLogs 
ORDER BY LEN(RawText) DESC;

-- Retrieve a calculated column showing the percentage of total reviews that are anomalies
SELECT 
    SUM(CAST(IsAnomaly AS INT)) * 100.0 / COUNT(*) AS AnomalyPercentage 
FROM SentimentLogs;

-- Retrieve reviews grouped by extraction date and data source to monitor pipeline health
SELECT CAST(ExtractionTimestamp AS DATE) AS ExtractionDate, DataSource, COUNT(*) AS RecordsProcessed 
FROM SentimentLogs 
GROUP BY CAST(ExtractionTimestamp AS DATE), DataSource;

-- Retrieve the top 3 reviews with the highest sentiment scores using a window function
WITH RankedReviews AS (
    SELECT *, ROW_NUMBER() OVER(ORDER BY SentimentScore DESC) AS RankRow 
    FROM SentimentLogs
)
SELECT * FROM RankedReviews 
WHERE RankRow <= 3;

-- Retrieve a running total of extracted reviews ordered by extraction timestamp
SELECT 
    ReviewID, 
    ExtractionTimestamp, 
    COUNT(ReviewID) OVER(ORDER BY ExtractionTimestamp ROWS UNBOUNDED PRECEDING) AS RunningTotal 
FROM SentimentLogs;

-- Retrieve the 5-row moving average of sentiment scores using a window function
SELECT 
    ReviewID, 
    ReviewDate, 
    SentimentScore, 
    AVG(SentimentScore) OVER(ORDER BY ReviewDate ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS MovingAvgSentiment 
FROM SentimentLogs;

-- Retrieve the rank of each review's sentiment score partitioned by star rating
SELECT 
    ReviewID, 
    StarRating, 
    SentimentScore, 
    RANK() OVER(PARTITION BY StarRating ORDER BY SentimentScore DESC) AS SentimentRank 
FROM SentimentLogs;

-- Retrieve a pivot-style result counting sentiment categories for each star rating
SELECT 
    StarRating,
    SUM(CASE WHEN Category = 'Positive' THEN 1 ELSE 0 END) AS PositiveCount,
    SUM(CASE WHEN Category = 'Neutral' THEN 1 ELSE 0 END) AS NeutralCount,
    SUM(CASE WHEN Category = 'Negative' THEN 1 ELSE 0 END) AS NegativeCount
FROM SentimentLogs
GROUP BY StarRating
ORDER BY StarRating DESC;

-- Retrieve the chronological difference in average sentiment score using LAG()
WITH DailySentiment AS (
    SELECT CAST(ReviewDate AS DATE) AS ReviewDay, AVG(SentimentScore) AS AvgScore
    FROM SentimentLogs
    GROUP BY CAST(ReviewDate AS DATE)
)
SELECT 
    ReviewDay, 
    AvgScore, 
    LAG(AvgScore, 1) OVER(ORDER BY ReviewDay) AS PreviousDayScore,
    AvgScore - LAG(AvgScore, 1) OVER(ORDER BY ReviewDay) AS DayOverDayChange
FROM DailySentiment;

-- Retrieve the standard deviation and variance of sentiment scores grouped by category
SELECT 
    Category, 
    STDEV(SentimentScore) AS SentimentStandardDeviation, 
    VAR(SentimentScore) AS SentimentVariance 
FROM SentimentLogs 
GROUP BY Category;

-- Retrieve a comprehensive deep-dive using a CTE to isolate and analyze critical anomalies
WITH AnomalyDeepDive AS (
    SELECT 
        ReviewID, 
        StarRating, 
        SentimentScore, 
        Category, 
        RawText,
        CASE 
            WHEN StarRating <= 2 AND Category = 'Positive' THEN 'False Positive / Sarcasm'
            WHEN StarRating >= 4 AND Category = 'Negative' THEN 'False Negative / Context Error'
            ELSE 'Unknown Anomaly'
        END AS AnomalyType
    FROM SentimentLogs
    WHERE IsAnomaly = 1
)
SELECT * FROM AnomalyDeepDive 
ORDER BY StarRating ASC, SentimentScore DESC;