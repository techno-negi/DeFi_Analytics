import React, { useState, useEffect, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import './RealtimeChart.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const RealtimeChart = ({ dataStream, maxPoints = 50, label = 'Value' }) => {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [{
      label,
      data: [],
      borderColor: 'rgb(59, 130, 246)',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4
    }]
  });

  useEffect(() => {
    if (dataStream) {
      setChartData(prev => {
        const newLabels = [...prev.labels, new Date().toLocaleTimeString()];
        const newData = [...prev.datasets[0].data, dataStream.value];

        // Keep only last maxPoints
        if (newLabels.length > maxPoints) {
          newLabels.shift();
          newData.shift();
        }

        return {
          labels: newLabels,
          datasets: [{
            ...prev.datasets[0],
            data: newData
          }]
        };
      });
    }
  }, [dataStream, maxPoints]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 0
    },
    scales: {
      y: {
        beginAtZero: false,
        grid: {
          color: 'rgba(255, 255, 255, 0.1)'
        },
        ticks: {
          color: '#9ca3af'
        }
      },
      x: {
        grid: {
          display: false
        },
        ticks: {
          color: '#9ca3af',
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 10
        }
      }
    },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        titleColor: '#f3f4f6',
        bodyColor: '#d1d5db',
        borderColor: '#374151',
        borderWidth: 1
      }
    }
  };

  return (
    <div className="realtime-chart">
      <Line data={chartData} options={options} />
    </div>
  );
};

export default RealtimeChart;
