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
  subtitle?: string;
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
  subtitle,
  zoneId,
}: TrendChartProps) {
  const [liveData, setLiveData] = React.useState<TrendDataPoint[]>([]);

  React.useEffect(() => {
    if (!zoneId) return;

    import('@/lib/websocket').then(({ SensorWebSocketClient }) => {
      const wsClient = new SensorWebSocketClient();

      const unsubscribe = wsClient.onMessage((msg) => {
        if (msg.type === 'telemetry_update' && msg.sensor_reading.zone_id === zoneId) {
          const { sensor_reading, timestamp } = msg;
          const timeLabel = new Date(timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          });

          setLiveData((prev) => {
            const next = [
              ...prev,
              {
                time: timeLabel,
                displacement: sensor_reading.displacement_mm_day,
                velocity: msg.risk_prediction.displacement_velocity_mm_day,
                porePressure: sensor_reading.pore_pressure,
              },
            ];
            return next.slice(-20);
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
    <div className="w-full p-6 bg-white border border-[#E6E8EE] rounded-2xl">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-[17px] md:text-[18px] font-semibold tracking-[-0.01em] text-[#0B1220]">
            {title}
          </h3>
          {subtitle && (
            <p className="text-[13px] text-[#5B6472] mt-0.5">{subtitle}</p>
          )}
        </div>
        <span className="text-[10px] font-mono uppercase tracking-[0.18em] px-2.5 py-1 rounded-full bg-[#EFF4FF] border border-[#2563EB]/20 text-[#2563EB]">
          {liveData.length > 0 ? 'Live Telemetry' : 'Sample Feed'}
        </span>
      </div>

      <div className="h-64 sm:h-72 md:h-80 w-full mt-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={displayData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid stroke="#EEF1F5" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="#5B6472"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: '#E6E8EE' }}
            />
            <YAxis
              stroke="#5B6472"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: '#E6E8EE' }}
            />
            <Tooltip
              contentStyle={{
                background: '#FFFFFF',
                border: '1px solid #E6E8EE',
                borderRadius: 12,
                fontSize: 12,
                boxShadow: '0 8px 30px rgba(15,23,42,0.08)',
                color: '#0B1220',
              }}
              labelStyle={{ color: '#0B1220', fontWeight: 600 }}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, color: '#5B6472', paddingTop: 8 }}
              iconType="circle"
            />
            <Line
              type="monotone"
              dataKey="displacement"
              name="Displacement (mm)"
              stroke="#2563EB"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#2563EB' }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="velocity"
              name="Velocity (mm/day)"
              stroke="#B91C1C"
              strokeWidth={2}
              dot={{ r: 3, fill: '#B91C1C' }}
            />
            <Line
              type="monotone"
              dataKey="porePressure"
              name="Pore Pressure (kPa)"
              stroke="#7C3AED"
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
