'use client';

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

export interface TrendDataPoint {
  time: string;
  displacement: number;
  velocity: number;
  porePressure: number;
}

interface TrendChartProps {
  data?: TrendDataPoint[];
  title?: string;
  zoneId?: string;
}

const mockTrendData: TrendDataPoint[] = [
  { time: '12:00', displacement: 2.1, velocity: 0.12, porePressure: 45 },
  { time: '13:00', displacement: 2.4, velocity: 0.15, porePressure: 47 },
  { time: '14:00', displacement: 2.8, velocity: 0.22, porePressure: 52 },
  { time: '15:00', displacement: 3.5, velocity: 0.38, porePressure: 61 },
  { time: '16:00', displacement: 4.9, velocity: 0.71, porePressure: 78 },
  { time: '17:00', displacement: 6.2, velocity: 1.15, porePressure: 95 },
  { time: '18:00', displacement: 8.0, velocity: 1.80, porePressure: 110 },
];

export default function TrendChart({
  data = mockTrendData,
  title = 'Sensor Telemetry Trends (Displacement vs Velocity)',
  zoneId,
}: TrendChartProps) {
  const [liveData, setLiveData] = React.useState<TrendDataPoint[]>([]);

  React.useEffect(() => {
    if (!zoneId) return; // if no zoneId, just use fallback data

    import('@/lib/websocket').then(({ SensorWebSocketClient }) => {
      const wsClient = new SensorWebSocketClient();
      
      const unsubscribe = wsClient.onMessage((msg) => {
        if (msg.type === 'telemetry_update' && msg.sensor_reading.zone_id === zoneId) {
          const { sensor_reading, timestamp } = msg;
          const timeLabel = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          
          setLiveData((prev) => {
            const next = [...prev, {
              time: timeLabel,
              displacement: sensor_reading.displacement_mm_day,
              velocity: msg.risk_prediction.displacement_velocity_mm_day,
              porePressure: sensor_reading.pore_pressure,
            }];
            return next.slice(-20); // Keep last 20 points
          });
        }
      });

      wsClient.connect();
      return () => {
        unsubscribe();
        wsClient.disconnect();
      };
    });
  }, [zoneId]);

  const displayData = liveData.length > 0 ? liveData : data;
  return (
    <div className="w-full p-6 bg-slate-900/80 border border-slate-800 rounded-xl shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-slate-100">{title}</h3>
        <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-400 font-mono">
          LIVE TELEMETRY
        </span>
      </div>

      <div className="h-[320px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={displayData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '8px',
                color: '#f8fafc',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
            <Line
              type="monotone"
              dataKey="displacement"
              name="Displacement (mm)"
              stroke="#38bdf8"
              strokeWidth={2.5}
              dot={{ r: 3 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="velocity"
              name="Velocity (mm/day)"
              stroke="#f43f5e"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
            <Line
              type="monotone"
              dataKey="porePressure"
              name="Pore Pressure (kPa)"
              stroke="#a855f7"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
