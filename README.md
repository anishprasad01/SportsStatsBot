# SportsStatsBot
A Slack Bolt Python Bot Learning Experience

## Currently Implemented Features

This bot is an exploration of the Slack Bolt application framework. It is a bot that gets information about the English Premier Football League (EPL) and displays it to the user in a number of forms.

In its present state, the bot can perform the following functions when requested either in a channel the bot is part of, or in a DM via the *Messaging Tab*:

* Retrieve the current league standings with the wins, losses, draws, and total points for each club, divided into home, and away totals.
* Get statistics for the club requested by the user. The information returned includes the team name and logo and home venue information. Additionally, the results include the wins, draws, losses, goals scored, and goals allowed. Again divided into home and away totals. The bot will also retrieve the results of the last three games the team played.
* Show the details of the past three games played in the entirety of the EPL, or the past three games played by a specific team if requested by the user. Data includes final score, venue, time, and home and away teams marked. 
* Show the details next three games scheduled to be played in the EPL, or the next three games a user-specified team is scheduled to play. Data includes predicted winner, venue, scheduled time, home and away teams marked, and season round.
* Ask the user for their favorite team, and store that information in an AWS DynamoDB table. Also allow the user to change, view, or delete their choice.

The bot also implements the *Home Tab* feature of Slack apps. The home tab offers persistent and updating information to the user when they open it. Firstly, it shows the current top three clubs in the EPL.
The tab will also show the next three games being played across the EPL. 
If the user's favorite team is stored in DynamoDB, the bot will personalize this tab with the user's favorite team name and the next three games their favorite team will play.

## Future Enhancements

This bot is currently in its early stages, and there are several potential paths along which it can evolve with further development.

* Performing requirements elicitation to identify features that potential users might want.
* Optimizing performance.
* Adding support for player stats, different leagues, or more sports.
* Using DynamoDB or other services to further personalize and enhance the user experience.
* Implementing a testing framework for long-term development.
* Evaluating and choosing a hosting vendor for deployment.
* Configuring CI/CD pipelines for smoother development and testing.
* Performing security hardening and testing prior to public availablity.
