import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import './NetworkGraph.css';

const NetworkGraph = ({ nodes, links, width = 800, height = 600 }) => {
  const svgRef = useRef();

  useEffect(() => {
    if (!nodes || !links || nodes.length === 0) return;

    // Clear previous graph
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    // Create links
    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#6b7280')
      .attr('stroke-width', d => Math.sqrt(d.value || 1))
      .attr('stroke-opacity', 0.6);

    // Create nodes
    const node = svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', d => d.size || 10)
      .attr('fill', d => d.color || '#3b82f6')
      .attr('stroke', '#1f2937')
      .attr('stroke-width', 2)
      .call(drag(simulation));

    // Add labels
    const label = svg.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .text(d => d.label)
      .attr('font-size', 12)
      .attr('dx', 15)
      .attr('dy', 4)
      .attr('fill', '#d1d5db');

    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);

      label
        .attr('x', d => d.x)
        .attr('y', d => d.y);
    });

    // Drag behavior
    function drag(simulation) {
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }

      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }

      function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }

      return d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
    }

    return () => {
      simulation.stop();
    };
  }, [nodes, links, width, height]);

  return (
    <div className="network-graph">
      <svg ref={svgRef}></svg>
    </div>
  );
};

export default NetworkGraph;
