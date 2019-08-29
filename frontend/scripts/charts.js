/* jshint esversion: 6 */
(function ($) {
  const contexts = $('.dccn-scores-bar-chart');
  //
  // Define some constants:
  //
  const BG_COLORS = [
    'rgba(255, 99, 132, 0.2)',
    'rgba(54, 162, 235, 0.2)',
    'rgba(255, 206, 86, 0.2)',
    'rgba(75, 192, 192, 0.2)'
  ];
  const BORDER_COLORS = [
    'rgba(255, 99, 132, 1)',
    'rgba(54, 162, 235, 1)',
    'rgba(255, 206, 86, 1)',
    'rgba(75, 192, 192, 1)'
  ];
  const CATEGORIES = ['Technical Merit', 'Clarity', 'Relevance', 'Originality'];
  const MAX_REVIEWS = 3;

  contexts.each((index, ctx) => {

    //
    // 1) First, we parse 'data-scores' attribute value. It stores the
    //    review scores (from each reviewer), separated with ',' between
    //    scores and with ';' between reviewers. Example:
    //      '2,3,4,5;1,2,1,2'
    //   - two reviewers, first gave [2, 3, 4, 5] and second gave [1, 2, 1, 2].
    const allScoresString = $(ctx).attr('data-scores');
    const allScores = allScoresString.split(';').map(s1 => {
      return s1.split(',').map(s2 => {
        return parseInt(s2);
      });
    });

    // 2) Validate data:
    const numReviews = allScores.length;
    const EXPECTED_CATEGORIES_NUM = CATEGORIES.length;
    let valid = numReviews > 0 && numReviews <= MAX_REVIEWS;
    allScores.forEach(scores => {
      valid = valid && scores.length === EXPECTED_CATEGORIES_NUM;
      scores.forEach(score => {
        valid = valid && !isNaN(score);
      });
    });

    if (valid) {
      // 3) If data is valid, we estimate average scores:
      const scoresSum = allScores.length > 1 ? math.add(...allScores) : allScores[0];
      const averages = math.divide(scoresSum, numReviews);

      // 4) Define data sets:
      const datasets = [];
      allScores.forEach((scores, index) => {
        datasets.push({
          label: `Review #${index+1}`,
          data: scores,
          backgroundColor: BG_COLORS[index],
          borderColor: BORDER_COLORS[index],
          borderWidth: 1
        });
      });
      // ... also add data for averages (they are plotted with line):
      datasets.push({
        label: 'Average',
        data: averages,
        backgroundColor: BG_COLORS[numReviews],
        borderColor: BORDER_COLORS[numReviews],
        type: 'line',
        fill: false
      });

      // 5) Finally, we can plot!
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: CATEGORIES,
          datasets: datasets,
        },
        options: {scales: {yAxes: [{ticks: {beginAtZero: true}}]}}
      });
    }
  });
}(jQuery));
