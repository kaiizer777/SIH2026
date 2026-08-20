'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { TopBar, type FilterPillOption } from '@/components/topbar/TopBar';
import { ChapterHeader } from '@/components/ui/ChapterHeader';
import { CopyButton } from '@/components/ui/CopyButton';
import { SensorWebSocketClient } from '@/lib/websocket';
import { AlertEventMessage } from '@/lib/types';

// Map backend AlertEvent to UI Alert structure
interface UIAlert {
  id: string;
  timestamp: string;
  level: string; // 'evacuation' | 'warning' | 'advisory' | 'safe'
  zone: string;
  sensorId: string;
  message: string;
  probability: number;
  status: string;
}

const mockAlerts: UIAlert[] = [
  {
    id: 'ALT-9042',
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    level: 'evacuation',
    zone: 'North Highwall - Bench 4',
    sensorId: 'RADAR-01',
    message:
      'Inverse-velocity threshold breached: 1.80 mm/day acceleration detected. Immediate bench evacuation recommended.',
    probability: 0.88,
    status: 'active',
  },
  {
    id: 'ALT-9041',
    timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    level: 'warning',
    zone: 'East Haul Road - Ramp 2',
    sensorId: 'EXT-08',
    message:
      'Extensometer pore pressure surge (+32 kPa) following monsoon rainfall event. Speed limits enforced.',
    probability: 0.58,
    status: 'acknowledged',
  },
  {
    id: 'ALT-9040',
    timestamp: new Date(Date.now() - 1000 * 60 * 80).toISOString(),
    level: 'advisory',
    zone: 'West Pit Crest',
    sensorId: 'METEO-02',
    message: 'Rainfall intensity exceeds 15 mm/hr. Ground moisture saturation approaching advisory threshold.',
    probability: 0.35,
    status: 'active',
  },
  {
    id: 'ALT-9039',
    timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    level: 'safe',
    zone: 'South Slope Bench',
    sensorId: 'SEIS-03',
    message: 'Micro-seismic tremors normalized below background baseline. Nominal operations resumed.',
    probability: 0.12,
    status: 'resolved',
  },
];

type AlertFilter = 'all' | 'evacuation' | 'warning' | 'advisory' | 'safe';

const alertFilterPills: FilterPillOption<AlertFilter>[] = [
  { id: 'all', label: 'All Alerts' },
  { id: 'evacuation', label: 'Evacuation' },
  { id: 'warning', label: 'Warning' },
  { id: 'advisory', label: 'Advisory' },
  { id: 'safe', label: 'Safe / Resolved' },
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<UIAlert[]>(mockAlerts);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<AlertFilter>('all');
  const [dispatchedIds, setDispatchedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const wsClient = new SensorWebSocketClient();

    const unsubscribe = wsClient.onMessage((msg) => {
      if (msg.type === 'alert_event') {
        const { alert, timestamp } = msg as AlertEventMessage;

        const newAlert: UIAlert = {
          id: alert.alert_id,
          timestamp: alert.triggered_at || timestamp,
          level: alert.severity,
          zone: alert.zone_id,
          sensorId: 'SYS-RADAR',
          message: alert.message,
          probability:
            alert.severity === 'evacuation'
              ? 0.92
              : alert.severity === 'warning'
              ? 0.62
              : 0.18,
          status: alert.acknowledged ? 'acknowledged' : 'active',
        };

        setAlerts((prev) => [newAlert, ...prev].slice(0, 50));
      }
    });

    wsClient.connect();
    return () => {
      unsubscribe();
      wsClient.disconnect();
    };
  }, []);

  const handleAcknowledge = (id: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: 'acknowledged' } : a)),
    );
  };

  const handleDispatch = (id: string) => {
    setDispatchedIds((prev) => new Set([...prev, id]));
  };

  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      const matchFilter =
        filter === 'all' || a.level.toLowerCase() === filter.toLowerCase();
      const matchQuery =
        !query ||
        a.id.toLowerCase().includes(query.toLowerCase()) ||
        a.zone.toLowerCase().includes(query.toLowerCase()) ||
        a.message.toLowerCase().includes(query.toLowerCase()) ||
        a.sensorId.toLowerCase().includes(query.toLowerCase());
      return matchFilter && matchQuery;
    });
  }, [alerts, filter, query]);

  return (
    <div className="min-h-screen text-[#0B1220]" style={gradientStyle}>
      <TopBar
        query={query}
        setQuery={setQuery}
        activeFilter={filter}
        setActiveFilter={setFilter}
        filterPills={alertFilterPills}
        placeholder="Filter by zone, ID, sensor, or message…"
        activeRoute="/alerts"
      />

      <main className="max-w-5xl mx-auto px-5 sm:px-6 md:px-10 pb-24 pt-6 md:pt-10">
        <ChapterHeader
          num="LOG"
          title="Real-Time Alert Dispatch & Incident Logs"
          subtitle="Automated threshold triggers, audible siren status, and geotechnical incident response audit trail."
        />

        {/* Stats Hairline Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#E6E8EE] border border-[#E6E8EE] rounded-2xl overflow-hidden shadow-sm my-8">
          <div className="bg-white p-5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
              Total Logged
            </div>
            <div className="text-[24px] font-semibold font-mono text-[#0B1220]">
              {alerts.length}
            </div>
            <div className="text-[12px] text-[#5B6472]">Last 24 Hours</div>
          </div>

          <div className="bg-white p-5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#B91C1C]">
              Active Evacuations
            </div>
            <div className="text-[24px] font-semibold font-mono text-[#B91C1C]">
              {alerts.filter((a) => a.level === 'evacuation' && a.status === 'active').length}
            </div>
            <div className="text-[12px] text-[#B91C1C]">Immediate Action</div>
          </div>

          <div className="bg-white p-5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#B45309]">
              Warnings Under Watch
            </div>
            <div className="text-[24px] font-semibold font-mono text-[#B45309]">
              {alerts.filter((a) => a.level === 'warning').length}
            </div>
            <div className="text-[12px] text-[#B45309]">Monitored</div>
          </div>

          <div className="bg-white p-5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#047857]">
              Siren Response Time
            </div>
            <div className="text-[24px] font-semibold font-mono text-[#047857]">
              &lt; 2.5s
            </div>
            <div className="text-[12px] text-[#047857]">WebSocket Loop</div>
          </div>
        </div>

        {/* Alert List Rows (Matching PitchRow Pattern) */}
        <section className="mt-8">
          <div className="flex items-baseline justify-between border-b border-[#E6E8EE] pb-3">
            <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
              Showing {filteredAlerts.length} of {alerts.length} Incidents
            </span>
            {query && (
              <button
                onClick={() => setQuery('')}
                className="text-[11px] font-mono text-[#2563EB] hover:underline"
              >
                Clear search filter
              </button>
            )}
          </div>

          {filteredAlerts.length === 0 ? (
            <div className="py-16 text-center text-[#5B6472]">
              No alerts match the selected criteria.
            </div>
          ) : (
            <div className="divide-y divide-[#E6E8EE]">
              {filteredAlerts.map((alert, idx) => {
                const isEvac = alert.level.toLowerCase() === 'evacuation';
                const isWarn = alert.level.toLowerCase() === 'warning';
                const isAdvisory = alert.level.toLowerCase() === 'advisory';

                const badgeTone = isEvac
                  ? 'bg-rose-50 text-[#B91C1C] border-rose-200'
                  : isWarn
                  ? 'bg-amber-50 text-[#B45309] border-amber-200'
                  : isAdvisory
                  ? 'bg-blue-50 text-[#2563EB] border-blue-200'
                  : 'bg-emerald-50 text-[#047857] border-emerald-200';

                const numPrefix = `A${String(idx + 1).padStart(2, '0')}`;
                const isDispatched = dispatchedIds.has(alert.id);

                return (
                  <article key={alert.id} className="py-7 first:pt-6">
                    <div className="flex items-baseline gap-4 md:gap-6">
                      {/* Left Mono Label Column */}
                      <div className="flex-shrink-0 w-10 md:w-14 text-right">
                        <span
                          className={`text-[11px] font-mono uppercase tracking-[0.18em] ${
                            isEvac
                              ? 'text-[#B91C1C]'
                              : isWarn
                              ? 'text-[#B45309]'
                              : 'text-[#8A93A1]'
                          }`}
                        >
                          {numPrefix}
                        </span>
                      </div>

                      {/* Right Content Column */}
                      <div className="flex-1 min-w-0 space-y-3">
                        {/* Header Line */}
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-3">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-[0.14em] border ${badgeTone}`}
                            >
                              {alert.level}
                            </span>
                            <span className="font-mono text-[12px] text-[#8A93A1]">
                              {alert.id}
                            </span>
                            <span className="text-[12px] text-[#8A93A1]">
                              • {new Date(alert.timestamp).toLocaleTimeString()}
                            </span>
                          </div>

                          <span className="text-[10px] font-mono uppercase tracking-[0.14em] px-2 py-0.5 rounded-full bg-white border border-[#E6E8EE] text-[#5B6472]">
                            Status: <strong className="text-[#0B1220]">{alert.status}</strong>
                          </span>
                        </div>

                        {/* Zone Headline */}
                        <h3 className="text-[18px] md:text-[20px] font-semibold tracking-[-0.01em] text-[#0B1220] leading-[1.3]">
                          {alert.zone}
                        </h3>

                        {/* Message Description */}
                        <p className="text-[14.5px] text-[#1f2937] leading-[1.65]">
                          {alert.message}
                        </p>

                        {/* Technical Telemetry Metadata */}
                        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[12px] font-mono text-[#5B6472] pt-1">
                          <span>
                            Sensor:{' '}
                            <strong className="text-[#0B1220]">{alert.sensorId}</strong>
                          </span>
                          <span>
                            Rockfall Probability:{' '}
                            <strong
                              style={{
                                color: isEvac
                                  ? '#B91C1C'
                                  : isWarn
                                  ? '#B45309'
                                  : '#047857',
                              }}
                            >
                              {(alert.probability * 100).toFixed(0)}%
                            </strong>
                          </span>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                          <div className="flex flex-wrap items-center gap-2">
                            {alert.status === 'active' && !isAdvisory && (
                              <button
                                onClick={() => handleAcknowledge(alert.id)}
                                className="px-4 py-2 text-[12px] font-medium rounded-full bg-[#0B1220] hover:bg-[#1a2235] text-white transition shadow-sm"
                              >
                                {isEvac ? 'Acknowledge Siren' : 'Acknowledge Warning'}
                              </button>
                            )}

                            {alert.status === 'active' && isAdvisory && (
                              <button
                                onClick={() => handleAcknowledge(alert.id)}
                                className="px-4 py-2 text-[12px] font-medium rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white transition shadow-sm"
                              >
                                Acknowledge Advisory
                              </button>
                            )}

                            <button
                              onClick={() => handleDispatch(alert.id)}
                              disabled={isDispatched}
                              className={`px-4 py-2 text-[12px] font-medium rounded-full border transition ${
                                isDispatched
                                  ? 'bg-emerald-50 text-[#047857] border-emerald-200 cursor-default'
                                  : 'bg-white text-[#0B1220] border-[#E6E8EE] hover:border-[#0B1220]'
                              }`}
                            >
                              {isDispatched ? '✓ Team Dispatched' : 'Dispatch Geotech Team'}
                            </button>
                          </div>

                          <CopyButton
                            text={`[${alert.level.toUpperCase()}] ${alert.id} - ${alert.zone}\nTriggered: ${new Date(
                              alert.timestamp,
                            ).toLocaleString()}\nSensor: ${alert.sensorId}\nProbability: ${(
                              alert.probability * 100
                            ).toFixed(0)}%\nMessage: ${alert.message}`}
                          />
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

const gradientStyle: React.CSSProperties = {
  background:
    'radial-gradient(1200px 600px at 50% -200px, #EFF4FF 0%, #F7F9FF 35%, #FFFFFF 70%)',
  backgroundAttachment: 'fixed',
};
