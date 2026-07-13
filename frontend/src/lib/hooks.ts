"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { FieldOption } from "@/components/ResourceManager";

export function useOptions(endpoint: string, labelKey: string, valueKey = "id"): FieldOption[] {
  const [options, setOptions] = useState<FieldOption[]>([]);

  useEffect(() => {
    let active = true;
    api
      .get<Record<string, unknown>[]>(endpoint)
      .then((data) => {
        if (!active) return;
        setOptions(
          data.map((item) => ({
            value: String(item[valueKey]),
            label: String(item[labelKey]),
          })),
        );
      })
      .catch(() => {
        if (active) setOptions([]);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);

  return options;
}
