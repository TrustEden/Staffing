import dayjs from "dayjs";
import { useMemo } from "react";

const sampleShifts = [
  { id: "1", date: dayjs().add(1, "day"), role: "RN", status: "Open" },
  { id: "2", date: dayjs().add(2, "day"), role: "CNA", status: "Pending" }
];

function CalendarView() {
  const grouped = useMemo(() => {
    return sampleShifts.reduce((acc, shift) => {
      const key = shift.date.format("YYYY-MM-DD");
      acc[key] = acc[key] || [];
      acc[key].push(shift);
      return acc;
    }, {});
  }, []);

  return (
    <section>
      <h2>Upcoming Shifts</h2>
      <div className="calendar-list">
        {Object.entries(grouped).map(([date, shifts]) => (
          <div key={date} className="card">
            <h3>{dayjs(date).format("dddd, MMM D")}</h3>
            <ul>
              {shifts.map((shift) => (
                <li key={shift.id}>
                  <strong>{shift.role}</strong> – {shift.status}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

export default CalendarView;
