import React, { useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

const PublicationDashboard = () => {
  // Données sources (idéalement venant d'une API)
  const rawData = [
    { year: 2020, total: 450, oa: 210, details: { "Green": 40, "Gold": 50, "Diamond": 30, "Hybrid": 30, "Bronze": 20, "Other": 10, "Gold,Green": 30 } },
    { year: 2021, total: 480, oa: 250, details: { "Green": 45, "Gold": 60, "Diamond": 35, "Hybrid": 40, "Bronze": 20, "Other": 15, "Gold,Green": 35 } },
    { year: 2022, total: 500, oa: 300, details: { "Green": 50, "Diamond": 40, "Gold": 60, "Hybrid": 30, "Bronze": 20, "Other": 10, "Diamond,Green": 20, "Gold,Green": 30, "Hybrid,Green": 20, "Bronze,Green": 10, "Other,Green": 10 } },
    { year: 2023, total: 620, oa: 450, details: { "Green": 60, "Diamond": 55, "Gold": 80, "Hybrid": 40, "Bronze": 25, "Other": 15, "Diamond,Green": 45, "Gold,Green": 60, "Hybrid,Green": 35, "Bronze,Green": 20, "Other,Green": 15 } },
    { year: 2024, total: 750, oa: 580, details: { "Green": 70, "Diamond": 90, "Gold": 110, "Hybrid": 50, "Bronze": 30, "Other": 20, "Diamond,Green": 60, "Gold,Green": 70, "Hybrid,Green": 40, "Bronze,Green": 25, "Other,Green": 15 } },
    { year: 2025, total: 400, oa: 310, details: { "Green": 40, "Diamond": 50, "Gold": 60, "Hybrid": 30, "Bronze": 15, "Other": 10, "Diamond,Green": 30, "Gold,Green": 40, "Hybrid,Green": 20, "Bronze,Green": 15, "Other,Green": 10 } }
  ];

  // État pour les années sélectionnées
  const [yearRange, setYearRange] = useState({ start: 2022, end: 2025 });

  // Filtrage des données selon la plage sélectionnée
  const filteredData = useMemo(() => {
    return rawData.filter(d => d.year >= yearRange.start && d.year <= yearRange.end);
  }, [yearRange]);

  const colorMap = {
    "Gold": "#fac858", "Green": "#91cc75", "Diamond": "#73c0de",
    "Hybrid": "#ee6666", "Bronze": "#fc8452", "Other": "#7b7b7b", "Mixed": "#9a60b4"
  };

  const option = {
    title: { text: 'Accès Ouvert par Année', left: 'center' },
    // BOÎTE À OUTILS : Ajoute le bouton de téléchargement PNG
    toolbox: {
      feature: {
        saveAsImage: { 
          title: 'Télécharger PNG',
          name: `Publications_OA_${yearRange.start}_${yearRange.end}` 
        }
      },
      right: 10
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = filteredData[params[0].dataIndex];
        const percent = ((item.oa / item.total) * 100).toFixed(1);
        let html = `<div style="min-width:250px; font-family:sans-serif;">
          <div style="font-weight:bold; border-bottom:1px solid #eee; padding-bottom:5px; margin-bottom:5px;">Année ${item.year}</div>
          <div style="display:flex; justify-content:space-between;"><span>Total:</span> <b>${item.total}</b></div>
          <div style="display:flex; justify-content:space-between; color:#91cc75;"><span>Accès Ouvert:</span> <b>${item.oa} (${percent}%)</b></div>
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:5px; margin-top:10px; font-size:11px;">`;
        
        Object.entries(item.details).forEach(([key, val]) => {
          const color = colorMap[key.includes(',') ? "Mixed" : key] || "#ccc";
          html += `<div style="display:flex; align-items:center;">
            <span style="width:7px; height:7px; border-radius:50%; background:${color}; margin-right:5px;"></span>
            ${key}: <b>${val}</b>
          </div>`;
        });
        return html + `</div></div>`;
      }
    },
    legend: { data: ['Accès Ouvert', 'Accès Fermé'], bottom: 0 },
    xAxis: { type: 'category', data: filteredData.map(d => d.year) },
    yAxis: { type: 'value' },
    series: [
      {
        name: 'Accès Ouvert',
        type: 'bar',
        stack: 'total',
        data: filteredData.map(d => d.oa),
        itemStyle: { color: '#91cc75' },
        label: {
          show: true,
          position: 'inside',
          formatter: (p) => Math.round((p.value / filteredData[p.dataIndex].total) * 100) + '%'
        }
      },
      {
        name: 'Accès Fermé',
        type: 'bar',
        stack: 'total',
        data: filteredData.map(d => d.total - d.oa),
        itemStyle: { color: '#5470c6' }
      }
    ]
  };

  return (
    <div style={{ padding: '20px', maxWidth: '900px', margin: 'auto', background: '#fff', borderRadius: '12px', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
      
      {/* Sélecteurs d'années */}
      <div style={{ marginBottom: '30px', display: 'flex', gap: '20px', justifyContent: 'center', alignItems: 'center', background: '#f8f9fa', padding: '15px', borderRadius: '8px' }}>
        <label>
          De : 
          <select value={yearRange.start} onChange={e => setYearRange({...yearRange, start: parseInt(e.target.value)})}>
            {[2020, 2021, 2022, 2023, 2024, 2025].map(y => (
              <option key={y} value={y} disabled={y > yearRange.end}>{y}</option>
            ))}
          </select>
        </label>
        <label>
          À : 
          <select value={yearRange.end} onChange={e => setYearRange({...yearRange, end: parseInt(e.target.value)})}>
            {[2020, 2021, 2022, 2023, 2024, 2025].map(y => (
              <option key={y} value={y} disabled={y < yearRange.start}>{y}</option>
            ))}
          </select>
        </label>
      </div>

      <ReactECharts option={option} style={{ height: '500px' }} />
    </div>
  );
};

export default PublicationDashboard;