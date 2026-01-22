import { useRef, useEffect, useCallback } from 'react';
import { useSimulationStore } from '../../stores/simulationStore';
import type { Scooter, Station, ScooterGroupInfo } from '../../types/simulation';

// Battery level to color mapping (fallback when no group)
function getBatteryColor(level: number): string {
  if (level < 0.2) return '#EF4444';  // red - critical
  if (level < 0.4) return '#F97316';  // orange - low
  if (level < 0.6) return '#EAB308';  // yellow - medium
  if (level < 0.8) return '#84CC16';  // lime - good
  return '#22C55E';                    // green - full
}

// Scooter state to color mapping (for ring indicator)
function getScooterStateColor(state: string): string {
  switch (state) {
    case 'TRAVELING_TO_STATION':
      return '#3B82F6';  // blue
    case 'SWAPPING':
      return '#8B5CF6';  // purple
    case 'WAITING_FOR_BATTERY':
      return '#EF4444';  // red
    case 'IDLE':
      return '#9CA3AF';  // gray - idle
    default:
      return '#22C55E';  // green - moving
  }
}

// Get scooter fill color (uses group color if available, otherwise battery color)
function getScooterFillColor(
  scooter: Scooter,
  groupMap: Map<string, ScooterGroupInfo>
): string {
  // If scooter has a group, use group color
  if (scooter.group_id && groupMap.has(scooter.group_id)) {
    return groupMap.get(scooter.group_id)!.color;
  }
  // Otherwise use battery level color
  return getBatteryColor(scooter.battery_level);
}

// Apply opacity for IDLE scooters
function applyIdleOpacity(color: string, state: string): string {
  if (state === 'IDLE') {
    // Convert hex to rgba with 40% opacity
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, 0.4)`;
  }
  return color;
}

export function GridCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const {
    gridWidth,
    gridHeight,
    scooters,
    stations,
    scooterGroups,
  } = useSimulationStore();

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Create a map for quick group lookups
    const groupMap = new Map<string, ScooterGroupInfo>();
    scooterGroups.forEach(group => {
      groupMap.set(group.id, group);
    });

    // Get container dimensions
    const rect = container.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    // Set canvas size
    canvas.width = width;
    canvas.height = height;

    // Calculate cell size
    const cellWidth = width / gridWidth;
    const cellHeight = height / gridHeight;
    const cellSize = Math.min(cellWidth, cellHeight);

    // Calculate offset to center the grid
    const offsetX = (width - gridWidth * cellSize) / 2;
    const offsetY = (height - gridHeight * cellSize) / 2;

    // Clear canvas
    ctx.fillStyle = '#F3F4F6';
    ctx.fillRect(0, 0, width, height);

    // Draw grid lines (subtle)
    ctx.strokeStyle = '#E5E7EB';
    ctx.lineWidth = 0.5;
    for (let x = 0; x <= gridWidth; x++) {
      ctx.beginPath();
      ctx.moveTo(offsetX + x * cellSize, offsetY);
      ctx.lineTo(offsetX + x * cellSize, offsetY + gridHeight * cellSize);
      ctx.stroke();
    }
    for (let y = 0; y <= gridHeight; y++) {
      ctx.beginPath();
      ctx.moveTo(offsetX, offsetY + y * cellSize);
      ctx.lineTo(offsetX + gridWidth * cellSize, offsetY + y * cellSize);
      ctx.stroke();
    }

    // Draw stations
    stations.forEach((station: Station) => {
      const x = offsetX + station.position.x * cellSize;
      const y = offsetY + station.position.y * cellSize;
      const size = Math.max(cellSize * 3, 20);

      // Station background
      ctx.fillStyle = '#1F2937';
      ctx.beginPath();
      ctx.roundRect(x - size / 2, y - size / 2, size, size, 4);
      ctx.fill();

      // Battery fill indicator (shows full batteries only)
      const fillRatio = station.full_batteries / station.num_slots;
      ctx.fillStyle = fillRatio > 0.5 ? '#22C55E' : fillRatio > 0.2 ? '#EAB308' : '#EF4444';
      ctx.beginPath();
      ctx.roundRect(
        x - size / 2 + 2,
        y + size / 2 - 4 - (size - 8) * fillRatio,
        size - 4,
        (size - 8) * fillRatio,
        2
      );
      ctx.fill();

      // Station label (full batteries / total slots)
      ctx.fillStyle = '#FFFFFF';
      ctx.font = `${Math.max(10, cellSize * 0.8)}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${station.full_batteries}/${station.num_slots}`, x, y);
    });

    // Draw scooters
    scooters.forEach((scooter: Scooter) => {
      const x = offsetX + scooter.position.x * cellSize + cellSize / 2;
      const y = offsetY + scooter.position.y * cellSize + cellSize / 2;
      const radius = Math.max(cellSize / 3, 4);

      // Get fill color (group color or battery color)
      const fillColor = getScooterFillColor(scooter, groupMap);
      // Apply opacity for IDLE scooters
      ctx.fillStyle = applyIdleOpacity(fillColor, scooter.state);
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();

      // State indicator ring
      ctx.strokeStyle = getScooterStateColor(scooter.state);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y, radius + 2, 0, Math.PI * 2);
      ctx.stroke();

      // Draw line to target station if traveling
      if (scooter.state === 'TRAVELING_TO_STATION' && scooter.target_station_id) {
        const targetStation = stations.find(s => s.id === scooter.target_station_id);
        if (targetStation) {
          const tx = offsetX + targetStation.position.x * cellSize;
          const ty = offsetY + targetStation.position.y * cellSize;

          ctx.strokeStyle = 'rgba(59, 130, 246, 0.3)';
          ctx.lineWidth = 1;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(tx, ty);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }
    });
  }, [gridWidth, gridHeight, scooters, stations, scooterGroups]);

  // Animation loop
  useEffect(() => {
    let animationFrameId: number;

    const render = () => {
      draw();
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [draw]);

  // Handle resize
  useEffect(() => {
    const observer = new ResizeObserver(() => {
      draw();
    });

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [draw]);

  return (
    <div ref={containerRef} className="w-full h-full min-h-[400px]">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
      />
    </div>
  );
}
