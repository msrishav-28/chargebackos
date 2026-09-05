import { createContext, useContext } from "react";
import type { StaffUser } from "./ops-schemas";

export const StaffContext = createContext<StaffUser | null>(null);

export function useStaff() {
  const staff = useContext(StaffContext);
  if (!staff) throw new Error("Staff session must be verified before opening the console.");
  return staff;
}
