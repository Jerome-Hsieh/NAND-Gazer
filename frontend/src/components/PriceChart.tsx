import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { PricePoint } from '../types';

interface PriceChartProps {
  data: PricePoint[];
}

export default function PriceChart({ data }: PriceChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-white/30">
        No price data available
      </div>
    );
  }

  const chartData = data.map((p) => ({
    date: new Date(p.scraped_at).toLocaleDateString('zh-TW', {
      month: 'short',
      day: 'numeric',
    }),
    price: p.price,
    original_price: p.original_price,
    time: new Date(p.scraped_at).toLocaleString('zh-TW'),
  }));

  const prices = data.map((p) => p.price);
  const minPrice = Math.floor(Math.min(...prices) * 0.95);
  const maxPrice = Math.ceil(Math.max(...prices) * 1.05);

  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="date" tick={{ fontSize: 12, fill: 'rgba(255,255,255,0.5)' }} stroke="rgba(255,255,255,0.1)" />
        <YAxis domain={[minPrice, maxPrice]} tickFormatter={(v) => `$${v}`} tick={{ fontSize: 12, fill: 'rgba(255,255,255,0.5)' }} stroke="rgba(255,255,255,0.1)" />
        <Tooltip
          formatter={(value) => [`$${Number(value ?? 0).toLocaleString()}`, 'Price']}
          labelFormatter={(_, payload) => payload?.[0]?.payload?.time ?? ''}
          contentStyle={{
            background: 'rgba(20, 20, 40, 0.85)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '12px',
            color: '#f5f5f7',
          }}
          itemStyle={{ color: '#f5f5f7' }}
          labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
        />
        <Legend wrapperStyle={{ color: 'rgba(255,255,255,0.6)' }} />
        <Line
          type="monotone"
          dataKey="price"
          stroke="#ef4444"
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 6 }}
          name="Current Price"
        />
        {data.some((p) => p.original_price != null) && (
          <Line
            type="monotone"
            dataKey="original_price"
            stroke="rgba(255,255,255,0.3)"
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
            name="Original Price"
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
