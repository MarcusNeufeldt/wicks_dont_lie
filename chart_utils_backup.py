html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingView Chart</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        #chart-container {
            width: 100%;
            height: 500px;
            position: relative;
        }
        #chart {
            width: 100%;
            height: 100%;
        }
        #fullscreenButton, #screenshotButton {
            position: absolute;
            top: 10px;
            z-index: 10;
            padding: 5px 10px;
            background-color: white;
            border: 1px solid #cccccc;
            cursor: pointer;
        }
        #fullscreenButton {
            right: 10px;
        }
        #screenshotButton {
            right: 140px;
        }
        #notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            display: none;
            z-index: 1000;
        }
        #loadingIndicator {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: none;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 10px;
            border-radius: 5px;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div id="chart-container">
        <div id="chart"></div>
        <button id="fullscreenButton">Open Fullscreen</button>
        <button id="screenshotButton">Take Screenshot</button>
        <div id="loadingIndicator">Processing screenshot...</div>
    </div>
    <div id="notification"></div>
    <script>
        function createChart(data, wickLines) {
            const chartElement = document.getElementById('chart');
            const chartContainer = document.getElementById('chart-container');
            const chart = LightweightCharts.createChart(chartElement, {
                width: chartElement.offsetWidth,
                height: chartElement.offsetHeight,
                layout: {
                    backgroundColor: '#ffffff',
                    textColor: '#000000',
                },
                grid: {
                    vertLines: {
                        color: '#e0e0e0',
                    },
                    horzLines: {
                        color: '#e0e0e0',
                    },
                },
                priceScale: {
                    borderColor: '#cccccc',
                },
                timeScale: {
                    borderColor: '#cccccc',
                },
                localization: {
                    priceFormatter: price => price.toFixed(5),
                    timeFormatter: timestamp => {
                        const date = new Date(timestamp * 1000);
                        return date.toISOString().slice(0, 19).replace('T', ' ');
                    }
                },
            });

            const candleSeries = chart.addCandlestickSeries();
            candleSeries.setData(data);

            wickLines.forEach(line => {
                if (line.high_unfilled) {
                    const series = chart.addLineSeries({
                        color: 'rgba(255, 0, 0, 0.5)',
                        lineWidth: 3,
                        lineStyle: 2, // Dashed line
                    });
                    series.setData([
                        { time: line.time, value: line.high },
                        { time: line.endTime, value: line.high }
                    ]);
                }
                if (line.low_unfilled) {
                    const series = chart.addLineSeries({
                        color: 'rgba(0, 0, 255, 0.5)',
                        lineWidth: 3,
                        lineStyle: 2, // Dashed line
                    });
                    series.setData([
                        { time: line.time, value: line.low },
                        { time: line.endTime, value: line.low }
                    ]);
                }
            });

            const fullscreenButton = document.getElementById('fullscreenButton');
            const screenshotButton = document.getElementById('screenshotButton');

            fullscreenButton.addEventListener('click', () => {
                if (!document.fullscreenElement) {
                    if (chartContainer.requestFullscreen) {
                        chartContainer.requestFullscreen();
                    } else if (chartContainer.mozRequestFullScreen) { // Firefox
                        chartContainer.mozRequestFullScreen();
                    } else if (chartContainer.webkitRequestFullscreen) { // Chrome, Safari, and Opera
                        chartContainer.webkitRequestFullscreen();
                    } else if (chartContainer.msRequestFullscreen) { // IE/Edge
                        chartContainer.msRequestFullscreen();
                    }
                    fullscreenButton.innerText = 'Exit Fullscreen';
                } else {
                    if (document.exitFullscreen) {
                        document.exitFullscreen();
                    } else if (document.mozCancelFullScreen) { // Firefox
                        document.mozCancelFullScreen();
                    } else if (document.webkitExitFullscreen) { // Chrome, Safari, and Opera
                        document.webkitExitFullscreen();
                    } else if (document.msExitFullscreen) { // IE/Edge
                        document.msExitFullscreen();
                    }
                    fullscreenButton.innerText = 'Open Fullscreen';
                }
            });

            document.addEventListener('fullscreenchange', () => {
                if (!document.fullscreenElement) {
                    chart.resize(chartElement.offsetWidth, chartElement.offsetHeight);
                    fullscreenButton.innerText = 'Open Fullscreen';
                } else {
                    chart.resize(window.innerWidth, window.innerHeight);
                }
            });

            window.addEventListener('resize', () => {
                chart.resize(chartElement.offsetWidth, chartElement.offsetHeight);
            });

            screenshotButton.addEventListener('click', () => {
                const loadingIndicator = document.getElementById('loadingIndicator');
                loadingIndicator.style.display = 'block';

                html2canvas(chartContainer, { scale: 2 }).then(canvas => {
                    loadingIndicator.style.display = 'none';

                    // Always offer download as the primary method
                    downloadScreenshot(canvas);

                    // Try to copy to clipboard as a secondary method
                    if (navigator.clipboard && navigator.clipboard.write) {
                        canvas.toBlob(blob => {
                            navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
                                .then(() => {
                                    showNotification('Screenshot copied to clipboard and downloaded!');
                                })
                                .catch(err => {
                                    console.error('Failed to copy to clipboard:', err);
                                    showNotification('Screenshot downloaded. Clipboard copy failed.');
                                });
                        });
                    } else {
                        showNotification('Screenshot downloaded. Clipboard copy not supported in this browser.');
                    }
                }).catch(err => {
                    loadingIndicator.style.display = 'none';
                    console.error('Failed to capture screenshot:', err);
                    showNotification('Failed to capture screenshot. Please try again.', 'error');
                });
            });
        }

        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.style.backgroundColor = type === 'success' ? '#4CAF50' : '#f44336';
            notification.style.display = 'block';
            setTimeout(() => {
                notification.style.display = 'none';
            }, 20000);
        }

        function downloadScreenshot(canvas) {
            canvas.toBlob(blob => {
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'chart_screenshot.png';
                link.click();
                URL.revokeObjectURL(url);
            });
        }

        function getData() {
            const dataElement = document.getElementById('data-json');
            const wickLinesElement = document.getElementById('wick-lines-json');
            const data = JSON.parse(dataElement.textContent);
            const wickLines = JSON.parse(wickLinesElement.textContent);
            createChart(data, wickLines);
        }

        document.addEventListener('DOMContentLoaded', getData);
    </script>
    <div id="data-json" style="display: none;">{{ data }}</div>
    <div id="wick-lines-json" style="display: none;">{{ wick_lines }}</div>
</body>
</html>
"""