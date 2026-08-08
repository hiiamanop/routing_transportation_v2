// Ikon SVG inline (bukan emoji) -- dipakai bareng oleh page.tsx & MapComponent.tsx.
// Tanpa dependency baru: cukup path SVG minimal bergaya Google Material Symbols.
import { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const base = (props: IconProps) => ({
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  ...props,
});

export const SearchIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

export const SwapIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M7 10h13l-4-4M17 14H4l4 4" />
  </svg>
);

export const ClockIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 3" />
  </svg>
);

export const WalkIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <circle cx="13" cy="4" r="1.6" fill="currentColor" stroke="none" />
    <path d="M10 8l1.5 3-2 2-1 5M11.5 11l2.5 1.5 2 5M13 6l-2 4-3 1.5" />
  </svg>
);

export const VanIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M3 16V9a1 1 0 0 1 1-1h11l4 4v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z" />
    <circle cx="7.5" cy="17" r="1.6" />
    <circle cx="16.5" cy="17" r="1.6" />
  </svg>
);

export const BusIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <rect x="4" y="4" width="16" height="13" rx="2" />
    <path d="M4 11h16" />
    <circle cx="8" cy="19" r="1.4" />
    <circle cx="16" cy="19" r="1.4" />
  </svg>
);

export const TrainIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <rect x="5" y="3" width="14" height="13" rx="3" />
    <path d="M5 10h14" />
    <circle cx="9" cy="19" r="1.2" />
    <circle cx="15" cy="19" r="1.2" />
    <path d="M8 20l-1.5 2M16 20l1.5 2" />
  </svg>
);

export const TransferIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M7 7h10l-3-3M17 17H7l3 3" />
  </svg>
);

export const RouteDotIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <circle cx="12" cy="12" r="4" fill="currentColor" stroke="none" />
  </svg>
);

export const CarIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M4 16V11l2-5h12l2 5v5" />
    <path d="M4 16h16v2a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-1H7v1a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1Z" />
    <circle cx="7.5" cy="16" r="1.4" />
    <circle cx="16.5" cy="16" r="1.4" />
  </svg>
);

export const MotorbikeIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <circle cx="5.5" cy="17" r="2.5" />
    <circle cx="18.5" cy="17" r="2.5" />
    <path d="M5.5 17h6l2-7h3M13.5 10h3.5l2 4.5M9 10h4l1.5 3" />
    <path d="M17 17h1.5" />
  </svg>
);

export const AlertIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M12 3 2 21h20L12 3Z" />
    <path d="M12 10v4M12 17.5v.01" />
  </svg>
);

export const CloseIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M6 6l12 12M18 6 6 18" />
  </svg>
);

export const NavigationIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M3 11l18-8-8 18-2-8-8-2Z" />
  </svg>
);

export const UserIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 20c0-4 3.5-7 8-7s8 3 8 7" />
  </svg>
);

export const SlidersIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M4 6h10M18 6h2M4 18h2M10 18h10" />
    <circle cx="16" cy="6" r="2" fill="currentColor" stroke="none" />
    <circle cx="8" cy="18" r="2" fill="currentColor" stroke="none" />
  </svg>
);

export const MapIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M9 3 3 5v16l6-2 6 2 6-2V3l-6 2-6-2Z" />
    <path d="M9 3v16M15 5v16" />
  </svg>
);

export const ChevronDownIcon = (props: IconProps) => (
  <svg {...base(props)}>
    <path d="M6 9l6 6 6-6" />
  </svg>
);

export const LoaderIcon = (props: IconProps) => (
  <svg {...base(props)} className={`animate-spin ${props.className ?? ""}`}>
    <path d="M12 3a9 9 0 1 0 9 9" />
  </svg>
);

export function modeIcon(mode: string, props?: IconProps) {
  switch (mode) {
    case "WALK":
      return <WalkIcon {...props} />;
    case "PRIVATE_VEHICLE":
      return <MotorbikeIcon {...props} />;
    case "FEEDER_ANGKOT":
      return <VanIcon {...props} />;
    case "TEMAN_BUS":
      return <BusIcon {...props} />;
    case "LRT":
      return <TrainIcon {...props} />;
    default:
      return <TransferIcon {...props} />;
  }
}

export function modeLabel(mode: string): string {
  switch (mode) {
    case "WALK":
      return "Jalan kaki";
    case "PRIVATE_VEHICLE":
      return "Kendaraan pribadi";
    case "FEEDER_ANGKOT":
      return "Feeder Angkot";
    case "TEMAN_BUS":
      return "Teman Bus";
    case "LRT":
      return "LRT";
    default:
      return "Transit";
  }
}

// Palet warna per moda, dipakai konsisten di kartu rute & polyline peta.
export function modeColor(mode: string): string {
  switch (mode) {
    case "WALK":
      return "#5f6368"; // abu netral -- jalan kaki bukan "rute" bermoda
    case "PRIVATE_VEHICLE":
      return "#188038"; // hijau -- beda dari semua moda transit umum
    case "TEMAN_BUS":
      return "#1a73e8"; // biru Google
    case "FEEDER_ANGKOT":
      return "#d93025"; // merah (senada --gmaps-red)
    case "LRT":
      return "#8430ce"; // ungu
    default:
      return "#5f6368";
  }
}
