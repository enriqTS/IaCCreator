import { useTourStore } from '@/store/tour-store';

describe('tour-store', () => {
  beforeEach(() => {
    // Reset store state between tests
    const store = useTourStore.getState();
    useTourStore.setState({
      isActive: false,
      completed: false,
      currentPage: 0,
    });
    localStorage.clear();
  });

  it('starts with isActive=false, completed=false, currentPage=0', () => {
    const state = useTourStore.getState();
    expect(state.isActive).toBe(false);
    expect(state.completed).toBe(false);
    expect(state.currentPage).toBe(0);
  });

  describe('startTour', () => {
    it('sets isActive=true and currentPage=0', () => {
      useTourStore.setState({ isActive: false, currentPage: 3, completed: true });
      useTourStore.getState().startTour();

      const state = useTourStore.getState();
      expect(state.isActive).toBe(true);
      expect(state.currentPage).toBe(0);
    });
  });

  describe('nextPage', () => {
    it('advances currentPage by 1', () => {
      useTourStore.setState({ currentPage: 0 });
      useTourStore.getState().nextPage();
      expect(useTourStore.getState().currentPage).toBe(1);
    });

    it('clamps to max page index (4)', () => {
      useTourStore.setState({ currentPage: 4 });
      useTourStore.getState().nextPage();
      expect(useTourStore.getState().currentPage).toBe(4);
    });

    it('does not exceed bounds when called multiple times from last page', () => {
      useTourStore.setState({ currentPage: 4 });
      useTourStore.getState().nextPage();
      useTourStore.getState().nextPage();
      useTourStore.getState().nextPage();
      expect(useTourStore.getState().currentPage).toBe(4);
    });
  });

  describe('prevPage', () => {
    it('decreases currentPage by 1', () => {
      useTourStore.setState({ currentPage: 2 });
      useTourStore.getState().prevPage();
      expect(useTourStore.getState().currentPage).toBe(1);
    });

    it('clamps to 0 on first page', () => {
      useTourStore.setState({ currentPage: 0 });
      useTourStore.getState().prevPage();
      expect(useTourStore.getState().currentPage).toBe(0);
    });

    it('does not go below 0 when called multiple times', () => {
      useTourStore.setState({ currentPage: 0 });
      useTourStore.getState().prevPage();
      useTourStore.getState().prevPage();
      useTourStore.getState().prevPage();
      expect(useTourStore.getState().currentPage).toBe(0);
    });
  });

  describe('completeTour', () => {
    it('sets isActive=false and completed=true', () => {
      useTourStore.setState({ isActive: true, currentPage: 2 });
      useTourStore.getState().completeTour();

      const state = useTourStore.getState();
      expect(state.isActive).toBe(false);
      expect(state.completed).toBe(true);
    });
  });

  describe('persistence', () => {
    it('only persists the completed flag', () => {
      useTourStore.setState({ isActive: true, currentPage: 3, completed: true });

      const stored = JSON.parse(
        localStorage.getItem('diagram-editor:tour-state') || '{}',
      );
      expect(stored.state).toEqual({ completed: true });
    });
  });
});
