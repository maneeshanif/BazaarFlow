"use client";

export default function OrderCard({
  order,
}: {
  order: { id: string; customer: string; items: string; status: string };
}) {
  // Updated colors based on your 4-color palette
  const statusColor =
    order.status === "paid"
      ? "rgb(var(--brand-secondary))" // teal for paid
      : order.status === "pending"
      ? "rgb(var(--brand-accent))" // accent orange-beige for pending
      : "rgb(var(--brand-primary))"; // deep teal for others

  return (
    <div
      className="card"
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        backgroundColor: "rgb(var(--brand-light))", // light beige background
        borderColor: "rgb(var(--brand-secondary))",
      }}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 10,
            background: "linear-gradient(90deg, rgb(var(--brand-primary)), rgb(var(--brand-secondary)))",
          }}
        />
        <div>
          <div style={{ fontWeight: 700 }}>
            {order.customer}{" "}
            <span
              style={{ color: "rgb(var(--brand-secondary))", fontWeight: 500 }}
            >
              #{order.id}
            </span>
          </div>
          <div
            className="text-muted"
            style={{ marginTop: 6, color: "rgb(var(--brand-secondary))" }}
          >
            {order.items}
          </div>
        </div>
      </div>

      <div
        style={{
          textAlign: "right",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          gap: 8,
        }}
      >
        <div style={{ fontWeight: 700, color: statusColor }}>
          {order.status.toUpperCase()}
        </div>
        <div>
          <button
            className="btn-secondary"
            style={{ padding: "6px 10px", marginRight: 8 }}
          >
            Accept
          </button>
          <button className="btn-primary" style={{ padding: "6px 10px" }}>
            Details
          </button>
        </div>
      </div>
    </div>
  );
}





// "use client";

// export default function OrderCard({ order }: { order: { id: string; customer: string; items: string; status: string } }) {
//   // Use design tokens (accent variables) instead of hard-coded colors.
//   // paid -> accent-2 (green), pending -> accent-1 (brand blue), else muted gray
//   const statusColor = order.status === 'paid'
//     ? 'rgb(var(--accent-2))'
//     : order.status === 'pending'
//     ? 'rgb(var(--accent-1))'
//     : 'rgb(var(--muted))';
//   return (
//     <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
//       <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
//         <div style={{ width: 44, height: 44, borderRadius: 10, background: 'linear-gradient(90deg,var(--brand-1),var(--brand-2))' }} />
//         <div>
//           <div style={{ fontWeight: 700 }}>{order.customer} <span style={{ color: 'var(--muted)', fontWeight: 500 }}>#{order.id}</span></div>
//           <div className="text-muted" style={{ marginTop: 6 }}>{order.items}</div>
//         </div>
//       </div>

//       <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
//         <div style={{ fontWeight: 700, color: statusColor }}>{order.status.toUpperCase()}</div>
//         <div>
//           <button className="btn-secondary" style={{ padding: '6px 10px', marginRight: 8 }}>Accept</button>
//           <button className="btn-primary" style={{ padding: '6px 10px' }}>Details</button>
//         </div>
//       </div>
//     </div>
//   );
// }
