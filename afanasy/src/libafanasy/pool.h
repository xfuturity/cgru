#pragma once

#include "name_af.h"

#include "afnode.h"
#include "regexp.h"

namespace af
{
/// Afanasy render slave.
class Pool : public Node
{
public:

	Pool(const std::string &i_path);

	// To construct from store:
	Pool(int i_id = 0);

	Pool(Msg * msg);

	virtual ~Pool();

	inline const bool  isRoot() const { return m_name == "/"; }
	inline const bool notRoot() const { return m_name != "/"; }

	void v_generateInfoStream(std::ostringstream & stream, bool full = false) const;

	virtual int v_calcWeight() const; ///< Calculate and return memory size.

	virtual void v_jsonWrite(std::ostringstream & o_str, int type) const;

	bool jsonRead(const JSON & i_object, std::string * io_changes = NULL);

	inline bool isPaused() const { return (m_state & SPaused);}
	inline void setPaused(bool set) { m_state = set ? m_state | SPaused : m_state & (~SPaused); }

	inline int getMaxRunTasks() const { return m_max_run_tasks;}
	inline int getMaxRunTasksPerHost() const { return m_max_run_tasks_per_host;}

public:
	enum State
	{
		SPaused  = 1ULL << 0
	};

public:
	static const std::string FilterName(const std::string & i_name);

protected:
	RegExp m_pattern;

	std::string m_parent_path;

	int64_t m_time_creation;

	int32_t m_pools_num;
	int32_t m_pools_total;
	int32_t m_renders_num;
	int32_t m_renders_total;

	int64_t m_time_offline;
	int64_t m_time_empty;

	int32_t m_max_run_tasks;
	int32_t m_max_run_tasks_per_host;

	int64_t m_task_start_finish_time; ///< Task start or finish time.

	std::vector<std::string> m_services_disabled;

//	Host     m_host;

private:
	void initDefaultValues();

protected:
	void v_readwrite(Msg * msg); ///< Read or write Pool in message.
};
}