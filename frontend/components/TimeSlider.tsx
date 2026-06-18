"use client";

interface TimeSliderProps {
  dates: string[];
  selectedIdx: number;
  onChange: (idx: number) => void;
}

export default function TimeSlider({ dates, selectedIdx, onChange }: TimeSliderProps) {
  const selectedDate = dates[selectedIdx];

  return (
    <div className="time-slider-container">
      <div className="time-slider-label">
        <span>📅 8-Day Composites — Kharif 2025</span>
        <span className="time-slider-date">{selectedDate}</span>
      </div>

      <input
        type="range"
        className="slider"
        min={0}
        max={dates.length - 1}
        step={1}
        value={selectedIdx}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="Select 8-day composite date"
        id="time-slider"
      />

      {/* Tick marks */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 6,
        }}
      >
        {dates
          .filter((_, i) => i % 4 === 0 || i === dates.length - 1)
          .map((d) => (
            <span key={d} style={{ fontSize: 9, color: "var(--color-text-dim)" }}>
              {d.slice(5)} {/* MM-DD */}
            </span>
          ))}
      </div>
    </div>
  );
}
