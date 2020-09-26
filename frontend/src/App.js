import React, { createRef, useEffect, useRef, useState } from 'react';
import logo from './logo.svg';
import './App.css';
import * as d3 from 'd3';

function clamp(val, min, max) {
  return Math.max(Math.min(val, max), min);
}

function range(min, max) {
  return [...Array(max - min).keys()].map(x => min + x);
}

function generateData() {
  return {
    "clients": range(0, 28).map(i => ({
      mac: "" + i,
      x: 5 + Math.pow(Math.random(), 1) * 7,
      y: 1 + Math.pow(Math.random(), 1) * 18
    })),
    "scanners": [
      { x: 1, y: 9 },
      { x: 1, y: 19 },
      { x: 14, y: 19}
    ],
    "room": {
      top: 0,
      left: 0,
      right: 15,
      bottom: 20
    },
    "tables": [
      { x: 2, y: 1, width: 60, height: 60 },
      { x: 2, y: 5, width: 60, height: 60 },
      { x: 2, y: 12, width: 60, height: 60 },
      { x: 2, y: 16, width: 60, height: 60 },
      { x: 11, y: 1, width: 60, height: 60 },
      { x: 11, y: 5, width: 60, height: 60 },
      { x: 11, y: 12, width: 60, height: 60 },
      { x: 11, y: 16, width: 60, height: 60 },
    ]
  };
}

const example = generateData();

function random(min, max) {
  return min + Math.random() * (max - min);
}

const MOVEMENT_X = 0.2;
const MOVEMENT_Y = 0.4;

function moveClient(data, c) {
  const moved = Math.random() > 0.2;
  return {
    ...c,
    x: moved ? c.x : clamp(c.x + random(-MOVEMENT_X, MOVEMENT_X), data.room.left + 1, data.room.right),
    y: moved ? c.y : clamp(c.y + random(-MOVEMENT_Y, MOVEMENT_Y), data.room.top, data.room.bottom),
    pulse: !moved
  };
}

function randomizeData(data) {
  return {
    ...data,
    "clients": data.clients.map(c => moveClient(data, c))
  }
}

const WIDTH = 400;
const HEIGHT = 600;
const CLIENT_SIZE = 5;
const SCANNER_SIZE = 10;

function pulse(svg, data) {
  const transformX = x => (x - data.room.left) / (data.room.right - data.room.left) * WIDTH;
  const transformY = y => (y - data.room.top) / (data.room.bottom - data.room.top) * HEIGHT;

  for (const d of data.clients) {
    if (!d.pulse) continue;
    svg.append("circle")
      .attr("cx", transformX(d.x))
      .attr("cy", transformY(d.y))
      .attr("r", 5)
      .attr("opacity", 0.5)
      .attr("stroke", "#000000")
      .transition()
      .duration(1000)
      .attr("r", 15)
      .attr("opacity", 0)
      .remove();
  }
}

function App() {
  const diagram = useRef();
  const [data, setData] = useState(example);

  const transformX = x => (x - data.room.left) / (data.room.right - data.room.left) * WIDTH;
  const transformY = y => (y - data.room.top) / (data.room.bottom - data.room.top) * HEIGHT;

  useEffect(() => {
    const svg = d3.select(diagram.current)
      .append("svg")
      .style("width", WIDTH)
      .style("height", HEIGHT)
      .style("border", "2px dotted gray");
    const scanners = svg.selectAll(".scanners")
      .data(data.scanners)
      .enter()
      .append("rect")
      .attr("x", d => transformX(d.x) - SCANNER_SIZE / 2)
      .attr("y", d => transformY(d.y) - SCANNER_SIZE / 2)
      .attr("width", SCANNER_SIZE)
      .attr("height", SCANNER_SIZE)
      .attr("r", 5)
      .style("fill", "red");
    const tables = svg.selectAll(".tables")
      .data(data.tables)
      .enter()
      .append("rect")
      .attr("x", d => transformX(d.x))
      .attr("y", d => transformY(d.y))
      .attr("width", d => d.width)
      .attr("height", d => d.height)
      .attr("opacity", 0.33)
      .style("fill", "black");
    const clients = svg.selectAll(".clients")
      .data(data.clients)
      .enter()
      .append("circle")
      .attr("cx", d => transformX(d.x))
      .attr("cy", d => transformY(d.y))
      .attr("r", 5)
      .style("fill", "black");
    
    pulse(svg, data);
    
    const iv2 = setInterval(() => {
      setData(randomizeData(data));
    }, 1000);
    pulse(svg, data);
    return () => {
      clearInterval(iv2);
      svg.remove();
    };
  }, [data]);

  return (
    <div className="App">
      <h1>Customer Engagement and Region Tracing</h1>
      Current customers: {data.clients.length} <br /><br />
      <div className="diagram" ref={diagram}>

      </div>
    </div>
  );
}

export default App;
