import React from 'react';
import ReactECharts from 'echarts-for-react';

const PublicationStackedChart = () => {
  // Configuration des couleurs par type d'accès
  const colorMap = {
    "Gold": "#fac858",
    "Green": "#91cc75",
    "Diamond": "#73c0de",
    "Hybrid": "#ee6666",
    "Bronze": "#fc8452",
    "Other": "#7b7b7b",
    "Mixed": "#9a60b4" // Pour les types combinés (ex: Gold,Green)
  };

  const data = [
    {
      year: '2022',
      total: 500,
      oa: 300,
      details: { "Green": 50, "Diamond": 40, "Gold": 60, "Hybrid": 30, "Bronze": 20, "Other": 10, "Diamond,Green": 20, "Gold,Green": 30, "Hybrid,Green": 20, "Bronze,Green": 10, "Other,Green": 10 }
    },
    {
      year: '2023',
      total: 620,
      oa: 450,
      details: { "Green": 60, "Diamond": 55, "Gold": 80, "Hybrid": 40, "Bronze": 25, "Other": 15, "Diamond,Green": 45, "Gold,Green": 60, "Hybrid,Green": 35, "Bronze,Green": 20, "Other,Green": 15 }
    },
    {
      year: '2024',
      total: 750,
      oa: 580,
      details: { "Green": 70, "Diamond": 90, "Gold": 110, "Hybrid": 50, "Bronze": 30, "Other": 20, "Diamond,Green": 60, "Gold,Green": 70, "Hybrid,Green": 40, "Bronze,Green": 25, "Other,Green": 15 }
    },
    {
      year: '2025',
      total: 400,
      oa: 310,
      details: { "Green": 40, "Diamond": 50, "Gold": 60, "Hybrid": 30, "Bronze": 15, "Other": 10, "Diamond,Green": 30, "Gold,Green": 40, "Hybrid,Green": 20, "Bronze,Green": 15, "Other,Green": 10 }
    }
  ];

  const years = data.map(d => d.year);
  const oaValues = data.map(d => d.oa);
  const closedValues = data.map(d => d.total - d.oa);

  const option = {
    title: {
      text: 'Répartition des Publications (Accès Ouvert vs Fermé)',
      left: 'center',
      top: 10
    },
    legend: {
      data: ['Accès Ouvert', 'Accès Fermé'],
      bottom: 0
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const idx = params[0].dataIndex;
        const item = data[idx];
        const percent = ((item.oa / item.total) * 100).toFixed(1);

        let html = `<div style="font-family:sans-serif; min-width:280px;">
          <div style="font-weight:bold; font-size:14px; margin-bottom:8px; border-bottom:1px solid #eee; padding-bottom:4px;">
            Année ${item.year}
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span>Total Publications:</span> <b>${item.total}</b>
          </div>
          <div style="display:flex; justify-content:space-between; color:#91cc75; font-weight:bold; margin-bottom:8px;">
            <span>Accès Ouvert:</span> <span>${item.oa} (${percent}%)</span>
          </div>
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; font-size:11px; background:#f9f9f9; padding:8px; border-radius:4px;">`;

        Object.entries(item.details).forEach(([key, value]) => {
          // Logique de couleur : prend la couleur du premier mot ou "Mixed" si c'est une combinaison
          const colorKey = key.includes(',') ? "Mixed" : key;
          const color = colorMap[colorKey] || "#ccc";
          
          html += `<div style="display:flex; align-items:center;">
            <span style="width:8px; height:8px; border-radius:50%; background:${color}; margin-right:6px; flex-shrink:0;"></span>
            <span style="color:#666;">${key}:</span> <b style="margin-left:auto; padding-left:8px;">${value}</b>
          </div>`;
        });

        html += `</div></div>`;
        return html;
      }
    },
    xAxis: {
      type: 'category',
      data: years
    },
    yAxis: {
      type: 'value',
      name: 'Publications'
    },
    series: [
      {
        name: 'Accès Ouvert',
        type: 'bar',
        stack: 'total', // Indispensable pour l'empilement
        emphasis: { focus: 'series' },
        data: oaValues,
        itemStyle: { color: '#91cc75' },
        label: {
          show: true,
          position: 'inside',
          formatter: (p) => {
            const total = data[p.dataIndex].total;
            return Math.round((p.value / total) * 100) + '%';
          },
          color: '#fff',
          fontWeight: 'bold'
        }
      },
      {
        name: 'Accès Fermé',
        type: 'bar',
        stack: 'total',
        emphasis: { focus: 'series' },
        data: closedValues,
        itemStyle: { color: '#5470c6' }
      }
    ]
  };

  return (
    <div style={{ width: '100%', maxWidth: '800px', margin: '20px auto' }}>
      <ReactECharts 
        option={option} 
        style={{ height: '500px' }} 
        opts={{ renderer: 'canvas' }} 
      />
    </div>
  );
};

export default PublicationStackedChart;