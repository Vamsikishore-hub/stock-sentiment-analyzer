import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchDashboard, triggerRefresh } from '../services/api';

const POLL_INTERVAL = 60 * 1000; // 1 minute

export function useDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const intervalRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const result = await fetchDashboard();
      setData(result);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  const manualRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await triggerRefresh();
      // Wait a beat for the backend to process
      await new Promise(r => setTimeout(r, 3000));
      await load();
    } catch (err) {
      setError('Refresh failed: ' + err.message);
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  useEffect(() => {
    load();
    intervalRef.current = setInterval(load, POLL_INTERVAL);
    return () => clearInterval(intervalRef.current);
  }, [load]);

  return { data, loading, error, refreshing, lastUpdated, manualRefresh };
}
